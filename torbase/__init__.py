import os
import re
import time
from datetime import timedelta
from functools import wraps
import click
from dotenv import load_dotenv
from flask import Flask, abort, g, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import create_engine, event, select, func, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from .models import Base, User, Category, Post

def create_app(config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY'),
        DATABASE_URL=os.environ.get('DATABASE_URL'), MAX_CONTENT_LENGTH=65536,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE') == '1',
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30), WTF_CSRF_TIME_LIMIT=3600)
    app.config.update(config or {})
    if not app.config['SECRET_KEY'] or not app.config['DATABASE_URL']:
        raise RuntimeError('Run python scripts/configure.py first, or set SECRET_KEY and DATABASE_URL.')
    engine = create_engine(app.config['DATABASE_URL'], pool_pre_ping=True)
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def sqlite_fk(conn, record):
            conn.execute('PRAGMA foreign_keys=ON')
    app.extensions['engine'] = engine
    CSRFProtect(app)

    @app.before_request
    def open_db():
        g.db = Session(engine)
        g.user = g.db.get(User, session['uid']) if 'uid' in session else None

    @app.teardown_request
    def close_db(error):
        if 'db' in g:
            g.db.close()  # Rolls back any uncommitted work.

    @app.after_request
    def headers(response):
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        return response

    def login_required(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not g.user:
                return redirect(url_for('login'))
            return fn(*args, **kwargs)
        return wrapped

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error = None
        if request.method == 'POST':
            username = request.form.get('username', '').strip().lower()
            password = request.form.get('password', '')
            if len(username) > 64 or len(password) > 1024:
                abort(400)
            user = g.db.scalar(select(User).where(User.username == username))
            if user and check_password_hash(user.password_hash, password):
                session.clear()
                session['uid'] = user.id
                session.permanent = True
                return redirect(url_for('index'))
            error = 'Incorrect username or password.'
        return render_template('login.html', error=error)

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.get('/')
    @login_required
    def index():
        q = request.args.get('q', '').strip()[:160]
        stmt = select(Post, Category.name).join(Category).where(Post.user_id == g.user.id)
        if q:
            stmt = stmt.where(Post.title.startswith(q, autoescape=True))
        start = time.perf_counter()
        rows = g.db.execute(stmt.order_by(Post.title, Post.id).limit(100)).all()
        sql_ms = (time.perf_counter() - start) * 1000
        return render_template('index.html', rows=rows, q=q, sql_ms=sql_ms)

    def own_post(post_id):
        post = g.db.scalar(select(Post).where(Post.id == post_id, Post.user_id == g.user.id))
        if post is None:
            abort(404)
        return post

    @app.route('/posts/new', methods=['GET', 'POST'])
    @app.route('/posts/<int:post_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit(post_id=None):
        post = own_post(post_id) if post_id else None
        categories = g.db.scalars(select(Category).order_by(Category.name)).all()
        error = None
        if request.method == 'POST':
            title, body = request.form.get('title', '').strip(), request.form.get('body', '').strip()
            try:
                category_id = int(request.form.get('category_id', ''))
            except ValueError:
                abort(400)
            if not 1 <= len(title) <= 160 or not 1 <= len(body) <= 10000:
                error = 'Enter a title (1–160 characters) and note (1–10,000 characters).'
            elif not g.db.get(Category, category_id):
                error = 'Choose an existing category.'
            else:
                if post is None:
                    post = Post(user_id=g.user.id)
                    g.db.add(post)
                post.title, post.body, post.category_id = title, body, category_id
                g.db.commit()
                return redirect(url_for('index'))
        return render_template('edit.html', post=post, categories=categories, error=error)

    @app.post('/posts/<int:post_id>/delete')
    @login_required
    def delete(post_id):
        g.db.delete(own_post(post_id))
        g.db.commit()
        return redirect(url_for('index'))

    @app.get('/healthz')
    def health():
        g.db.execute(text('SELECT 1'))
        return {'status': 'ok'}

    @app.get('/benchmark')
    @login_required
    def benchmark():
        start = time.perf_counter()
        count = g.db.scalar(select(func.count()).select_from(Post).where(Post.user_id == g.user.id))
        return {'count': count, 'db_roundtrip_ms': (time.perf_counter() - start) * 1000}

    @app.cli.command('init-db')
    def init_db():
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            for name in ['Class notes', 'Research', 'Ideas']:
                if not db.scalar(select(Category).where(Category.name == name)):
                    db.add(Category(name=name))
            db.commit()
        click.echo('Schema and categories ready. Existing records preserved.')

    @app.cli.command('create-user')
    @click.argument('username')
    @click.password_option(confirmation_prompt=True)
    def create_user(username, password):
        username = username.strip().lower()
        if not re.fullmatch(r'[a-z0-9_-]{3,64}', username) or not 12 <= len(password) <= 1024:
            raise click.ClickException('Use a 3–64 character username (a-z, 0-9, _, -) and a 12+ character password.')
        with Session(engine) as db:
            db.add(User(username=username, password_hash=generate_password_hash(password)))
            try:
                db.commit()
            except IntegrityError:
                raise click.ClickException('Username already exists.')
        click.echo('User created.')
    return app

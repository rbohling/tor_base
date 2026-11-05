import os
import re
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash
from torbase import create_app
from torbase.models import Base, User, Category, Post

@pytest.fixture
def app(tmp_path):
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only-key',
        'DATABASE_URL': os.environ.get('TEST_DATABASE_URL', f'sqlite:///{tmp_path}/test.db')})
    engine = app.extensions['engine']
    # TEST_DATABASE_URL must point to a disposable test schema.
    Base.metadata.drop_all(engine)
    runner = app.test_cli_runner()
    assert runner.invoke(args=['init-db']).exit_code == 0
    with Session(engine) as db:
        db.add_all([User(username='alice', password_hash=generate_password_hash('alice-test-password')),
                    User(username='bob', password_hash=generate_password_hash('bob-test-password'))])
        db.commit()
    yield app
    Base.metadata.drop_all(engine)
    engine.dispose()

def token(response):
    return re.search(rb'name="csrf_token" value="([^"]+)"', response.data)[1].decode()

def login(client, name='alice'):
    csrf = token(client.get('/login'))
    return client.post('/login', data={'username':name,'password':f'{name}-test-password','csrf_token':csrf})

def add(client, title='A note', body='Private text'):
    return client.post('/posts/new', data={'csrf_token':token(client.get('/posts/new')),
        'title':title,'body':body,'category_id':'1'})

def test_login_and_logout(app):
    c=app.test_client()
    assert c.get('/').status_code==302
    assert login(c).status_code==302
    assert b'Your notes' in c.get('/').data
    assert c.get('/logout').status_code==405
    assert c.post('/logout',data={'csrf_token':token(c.get('/'))}).status_code==302
    assert c.get('/').status_code==302

def test_crud(app):
    c=app.test_client(); login(c)
    assert add(c).status_code==302
    assert b'Private text' in c.get('/').data
    r=c.get('/posts/1/edit')
    assert c.post('/posts/1/edit',data={'csrf_token':token(r),'title':'Updated','body':'Changed','category_id':2}).status_code==302
    assert b'Changed' in c.get('/').data
    assert c.post('/posts/1/delete',data={'csrf_token':token(c.get('/'))}).status_code==302
    assert b'No notes found' in c.get('/').data

def test_ownership_read_update_delete(app):
    a=app.test_client(); login(a); add(a)
    b=app.test_client(); login(b,'bob')
    assert b'Private text' not in b.get('/').data
    assert b.get('/posts/1/edit').status_code==404
    csrf=token(b.get('/'))
    assert b.post('/posts/1/edit',data={'csrf_token':csrf,'title':'Stolen','body':'x','category_id':1}).status_code==404
    assert b.post('/posts/1/delete',data={'csrf_token':csrf}).status_code==404
    assert b'Private text' in a.get('/').data

def test_csrf(app):
    c=app.test_client()
    assert c.post('/login',data={'username':'alice','password':'alice-test-password'}).status_code==400
    login(c)
    assert c.post('/posts/new',data={'title':'x'}).status_code==400
    assert c.post('/logout').status_code==400

def test_sql_injection_and_escaping(app):
    c=app.test_client(); login(c); add(c,'<script>alert(1)</script>')
    assert b'<script>' not in c.get('/').data
    assert b'&lt;script&gt;' in c.get('/').data
    assert b'No notes found' in c.get('/',query_string={'q':"' OR 1=1 --"}).data
    assert b'No notes found' in c.get('/',query_string={'q':'%'}).data

def test_invalid_form(app):
    c=app.test_client(); login(c)
    assert add(c,title='').status_code==200
    assert b'No notes found' in c.get('/').data
    assert c.post('/posts/new',data={'csrf_token':token(c.get('/posts/new')),'title':'x','body':'x','category_id':999}).status_code==200

def test_foreign_key_and_rollback(app):
    from sqlalchemy.exc import IntegrityError
    with Session(app.extensions['engine']) as db:
        db.add(Post(user_id=999,category_id=1,title='Invalid',body='x'))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
        db.add(Post(user_id=1,category_id=1,title='Not committed',body='x'))
        db.flush(); db.rollback()
        assert db.scalar(select(Post)) is None

def test_password_and_headers(app):
    with Session(app.extensions['engine']) as db:
        assert db.get(User,1).password_hash != 'alice-test-password'
    c=app.test_client(); login(c)
    r=c.get('/')
    assert r.headers['Cache-Control']=='no-store'
    assert "frame-ancestors 'none'" in r.headers['Content-Security-Policy']
    assert c.get('/benchmark').json['count']==0

def test_cli_validation(app):
    r=app.test_cli_runner()
    assert r.invoke(args=['create-user','alice','--password','long-enough-password']).exit_code !=0
    assert r.invoke(args=['create-user','newuser','--password','short']).exit_code !=0
    assert r.invoke(args=['create-user','newuser','--password','long-enough-password']).exit_code==0
    assert r.invoke(args=['init-db']).exit_code==0

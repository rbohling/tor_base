"""Add deterministic synthetic notes for an existing lab user, once per title."""
import argparse
from sqlalchemy import select
from sqlalchemy.orm import Session
from torbase import create_app
from torbase.models import User, Category, Post
p=argparse.ArgumentParser(); p.add_argument('username'); p.add_argument('--count',type=int,default=20000)
a=p.parse_args()
if not 1 <= a.count <= 100000: p.error('count must be 1–100000')
app=create_app()
with Session(app.extensions['engine']) as db:
    user=db.scalar(select(User).where(User.username==a.username))
    if not user: p.error('Create the user first.')
    cats=db.scalars(select(Category.id).order_by(Category.id)).all()
    if not cats: p.error('Run init-db first.')
    existing=set(db.scalars(select(Post.title).where(Post.user_id==user.id)))
    count=0
    for i in range(a.count):
        title=f'Lab {i:06d}'
        if title not in existing:
            db.add(Post(user_id=user.id,category_id=cats[i%len(cats)],title=title,
                body=f'Synthetic research note {i}. No personal information.'))
            count+=1
    db.commit()
print(f'Added {count} synthetic notes.')

from flask import Flask
from flask import render_template as rt
from flask import g, flash, redirect, url_for, session, request, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, ValidationError, validators
from passlib.hash import sha256_crypt
from functools import wraps

#from data import Articles


#Articles = Articles()

app = Flask(__name__)
# Mysql config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'wind0'
app.config['MYSQL_PASSWORD'] = 'test'
app.config['MYSQL_DB'] = 'SR'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MySQL
mysql = MySQL(app)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized', 'danger')
            return redirect(url_for('login'))
    return decorated_function


@app.route('/')
def index():
    return rt('home.html')


@app.route('/about')
def about():
    return rt('about.html')


@app.route('/articles/')
def articles():
    cur = mysql.connection.cursor()
    results = cur.execute('SELECT * FROM articles')
    articles = cur.fetchall()
    cur.close()
    if results>0:
        return rt('articles.html', articles=articles)
    else:
        msg = 'No articles found'
        return rt('articles.html')


@app.route('/article/<string:id>/')
def article(id):
    cur = mysql.connection.cursor()
    results = cur.execute('SELECT * FROM articles WHERE id = %s', [id])
    article = cur.fetchone()
    cur.close()
    return rt('article.html', article=article)


class RegisterForm(Form):
    name = StringField('Username', [validators.Length(min=1, max=50), validators.DataRequired()])
    password = PasswordField('New Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Confirm Password')
    code = StringField('Invite code', [validators.DataRequired()])

    def validate_code(self, code):
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM config")
        result = cur.fetchone()
        real_code = result['code']
        if str(code.data) != real_code:
            raise ValidationError('Incorrect code')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        password = sha256_crypt.encrypt(str(form.password.data))
        # create mysql cursor
        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO users(name,password) VALUES (%s,%s)", (name, password))
        mysql.connection.commit()
        # closing connection
        cur.close()
        flash('You are now registered','success')
        return redirect(url_for('login'))
    return rt('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password_candidate = request.form['password']

        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM users WHERE name = %s", [name])
        # if there is more than zero results
        if result > 0:
            data = cur.fetchone()
            password = data['password']
            if sha256_crypt.verify(password_candidate, password):
                session['logged_in'] = True
                session['username'] = name
                flash('Properly logged in', 'success')
                return redirect(url_for("dashboard"))
        else:
            error = "Incorrect credentials"
            return rt('/login.html', error=error)
    return rt('login.html')


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()
    results = cur.execute('SELECT * FROM articles')
    articles = cur.fetchall()
    cur.close()
    if results>0:
        return rt('dashboard.html', articles=articles)
    else:
        msg = 'No articles found'
        return rt('dashboard.html')


class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200), validators.DataRequired()])
    body = TextAreaField('Body', [validators.Length(min=30), validators.DataRequired()])


@app.route('/add_article', methods=['GET','POST'])
@login_required
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        cur = mysql.connection.cursor()
        cur.execute('INSERT INTO articles(title,body, author) VALUES(%s,%s,%s)',(title, body, session['username']))
        mysql.connection.commit()
        cur.close()

        flash('Article created', 'success')
        return redirect(url_for('dashboard'))
    return rt('add_article.html', form=form)


@app.route('/edit_article/<string:id>', methods=['GET','POST'])
@login_required
def edit_article(id):
    cur = mysql.connection.cursor()
    result = cur.execute('SELECT * FROM articles WHERE id=%s',[id])
    article=cur.fetchone()
    form = ArticleForm(request.form)

    # Populate the form with the pre existing data
    form.title.data=article['title']
    form.body.data=article['body']
    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']


        cur.execute('UPDATE articles SET title=%s, body=%s WHERE id=%s',(title, body, article['id']))
        mysql.connection.commit()
        cur.close()

        flash('Article updated', 'success')
        return redirect(url_for('dashboard'))
    return rt('edit_article.html', form=form)

@app.route('/delete_article/<string:id>')
@login_required
def delete_article(id):
    cur = mysql.connection.cursor()
    cur.execute('DELETE FROM articles WHERE id=%s',[id])
    mysql.connection.commit()
    cur.close()
    flash('Article deleted','success')
    return redirect(url_for('dashboard'))

app.secret_key = 'super secret key'
if __name__ == '__main__':
    app.run(debug=True)
    #app.run()

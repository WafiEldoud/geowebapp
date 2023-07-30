from flask import Flask, render_template, redirect, request, session, url_for, flash
from flask_mysqldb import MySQL
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import subprocess
import pymysql
import os
import base64
import yaml
from flask_admin.contrib.sqla import ModelView
from flask_admin.actions import action
from flask_admin import Admin, BaseView, expose, AdminIndexView
from flask_mail import Mail, Message




app = Flask(__name__)


with open('web.yaml') as file:
    base = yaml.safe_load(file)

app.secret_key = base['secret_key']
app.config['MYSQL_HOST'] = base['host']
app.config['MYSQL_USER'] = base['user']
app.config['MYSQL_PASSWORD'] = base['password']
app.config['MYSQL_DB'] = base['database']

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = base['email']
app.config['MAIL_PASSWORD'] = base['email_password']
app.config['MAIL_DEFAULT_SENDER'] = base['email']

app.config['FLASK_ADMIN_FLUID_LAYOUT'] = True

mydb = pymysql.connect(
    host=base['host'],
    user=base['user'],
    password=base['password'],
    database=base['database'],
    autocommit=True,
    charset='utf8mb4',
    
    )

mail = Mail(app)

mysql = MySQL(app)


base_url = 'mysql://{user}:{password}@{host}/{database}'.format(
    user=base['user'],
    password=base['password'],
    host=base['host'],
    database=base['database']
)
app.config['SQLALCHEMY_DATABASE_URI'] = base_url
db = SQLAlchemy(app)

class myadminhome(AdminIndexView):
    def is_accessible(self):
        return session.get('loggedin') and session.get('username') == base['coordinator']
    @expose('/admin_home')
    def admin_home(self):
        return super(myadminhome, self).index()

admin = Admin(app, name='ADMIN', template_mode='bootstrap4', index_view=myadminhome(name='DASHBOARD'))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    email = db.Column(db.String(50))
    person_code = db.Column(db.Integer)
    approved = db.Column(db.Boolean, default=0) 

    
    def __repr__(self):
        return self.user_name
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
class UserAdminView(ModelView):
    column_list = ('username', 'email', 'person_code', 'approved')
    column_searchable_list = ('username', 'email')
    column_filters = ('username', 'email', 'approved')

    @action('approve', 'Approve')
    def action_approve(self, ids):
        try:
            ids = [int(id) for id in ids]
            
            users = User.query.filter(User.id.in_(ids))
            for user in users:
                user.approved = True

            db.session.commit()

        except Exception as e:
            db.session.rollback()
    
    @action('unapprove', 'Unapprove')
    def action_unapprove(self, ids):
        try:
            ids = [int(id) for id in ids]
            
            users = User.query.filter(User.id.in_(ids))
            for user in users:
                user.approved = False

            db.session.commit()

            
        except Exception as e:
            db.session.rollback()
            
    

    def is_accessible(self):
        return session.get('loggedin') and session.get('username') == base['coordinator']
    
    def on_model_change(self, form, model, is_created):
        if is_created:
            model.approved = True



class ContactMembersView(BaseView):
    def is_accessible(self):
        return session.get('loggedin') and session.get('username') == base['coordinator']
    @expose('/')
    def index(self):
        return self.render('admin/mail.html')
    
class ContactNewMembersView(BaseView):
    def is_accessible(self):
        return session.get('loggedin') and session.get('username') == base['coordinator']
    @expose('/')
    def index(self):
        return self.render('admin/mail_2.html')
    
class reloadhome(BaseView):
    def is_accessible(self):
        if request.method == 'POST':
            subprocess.call(['python', 'dashboard.py'])
        return session.get('loggedin') and session.get('username') == base['coordinator']
    @expose('/')
    def index(self):
        subprocess.call(['python', 'dashboard.py'])
        return redirect(url_for('home'))
    
class adminlogout(BaseView):
    
    @expose('/')
    def index(self):
        session.pop('loggedin', None)
        session.pop('username', None)
        return redirect(url_for('index'))


admin.add_view(reloadhome(name="HOME"))
admin.add_view(UserAdminView(User, db.session, 'ALL USERS'))
admin.add_view(ContactMembersView(name="CONTACT MEMBERS"))
admin.add_view(ContactNewMembersView(name="NOTIFY NEW MEMBERS"))
admin.add_view(adminlogout(name="LOGOUT"))


# Index page
@app.route('/')
def index():
    return render_template('index.html')



# Home page
@app.route('/home')
def home():
    value = base['coordinator']
    if 'username' in session:
        return render_template('home.html', username= session['username'], value= value)
    else:
        return render_template('login.html')



# Register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST':
        user_info = request.form
        user_name = user_info['username']
        user_email = user_info['email']
        user_pc = user_info['person_code']
        user_pass = user_info['password']
        cur = mysql.connection.cursor()
        cur2 = mysql.connection.cursor()
        cur3 = mysql.connection.cursor()
        cur4 = mysql.connection.cursor()

        cur2.execute("SELECT * FROM user WHERE username = %s", (user_name,))
        result_1 = cur2.fetchone()
        cur3.execute("SELECT * FROM user WHERE email = %s", (user_email,))
        result_2 = cur3.fetchone()
        cur4.execute("SELECT * FROM user WHERE person_code = %s", (user_pc,))
        result_3 = cur4.fetchone()
        if result_1:
            message = 'Username is already in use.'
            cur2.close()
            return render_template('login.html', message=message)
        if result_3:
            message = 'Person Code is already in use.'
            cur3.close()
            return render_template('login.html', message=message)
        if result_2:
            message = 'Email is already in use.'
            cur3.close()
            return render_template('login.html', message=message)
            
        else:
            cur.execute("INSERT INTO user"
                        "(username, email, person_code, password)" 
                        "VALUES(%s, %s,%s, %s)", (user_name, user_email, user_pc, user_pass))
            mysql.connection.commit()
            cur.close()
            message= 'Your data was submitted successfully. Pending approval.'
            return render_template('login.html', message=message)
    return render_template('login.html')

#Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    cursor = mydb.cursor()
    message = ''
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor.execute('SELECT * FROM user WHERE username=%s AND password=%s', (username, password))
        record = cursor.fetchone()
        if record:
            if record[5] == 1: 
                session['loggedin'] = True
                session['ID'] = record[0]
                session['username'] = record[1]
                session['person_code'] = record[3]
                cursor.close()
                return redirect(url_for('home'))
            else:
                message = 'Member approval pending.'
                return render_template('login.html', message=message)
        else:
            message = 'Incorrect username and/or password.'
    return render_template('login.html', message=message)

#Input data
@app.route('/input', methods=['GET', 'POST'])
def input():
    if request.method == 'POST':
        message = ''
        user = session['username']
        cur2 = mysql.connection.cursor()
        cur2.execute('SELECT username FROM student_data')
        result = cur2.fetchall()
        names = [i[0] for i in result]
        if user in names:
            cur2.close()
            message= 'User data already stored.'
            return render_template('user_input.html', message=message, username= session['username'])
        else:
            
            member = request.form
            user_id = session['ID']
            first_name = member['first_name']
            surname = member['surname']
            username = user
            person_code = session['person_code']
            gender = member['gender']
            birthday = member['birthday']
            under_grad = member['under_grad']
            university = member['university']
            region = member['region']
            nationality = member['nationality']
            city = member['city']
            latitude = member['latitude']
            longitude = member['longitude']
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO student_data"
                            "(user_id, name, surname, username, person_code, gender, birth_date, under_grad, university, region, nationality, city, latitude, longitude)" 
                            "VALUES(%s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (user_id, first_name, surname, username, person_code, gender, birthday, under_grad, university, region, nationality, city, latitude, longitude))
            mysql.connection.commit()
            cur.close()
            
            message= 'Your data was stored successfully.'
            
            return render_template('redirect.html', message=message, username= session['username'])
                
    else:
            username= session['username']
            return render_template('user_input.html', username= session['username'])

# Upload the user's image
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['photo']
        if file:
            username = session['username']
            user_id = session['ID']
            file_extension = os.path.splitext(file.filename)[1]
            file_name = f"{username}{file_extension}"
            file_content = file.read()
            
            cursor = mydb.cursor()
            cursor.execute('''INSERT INTO uploaded_files (user_id, file_content, file_name, file_extension, username)
                              VALUES (%s, %s, %s, %s, %s)''', (user_id, file_content, file_name, file_extension, username))
            mydb.commit()
            cursor.close()
            message = 'Photo uploaded successfully.'

            return render_template('profile.html', message=message, username=session['username'], value=base['coordinator'])
    else:
        message = 'Please try again.'
        return render_template('upload.html', username=session['username'], value=base['coordinator'])


# Publish the user's data to their porfile
@app.route('/data', methods=['GET', 'POST'])
def data():
    user = session['username']
    image_base64 = ""
    photos= []
    cursor = mydb.cursor()
    cursor_2 = mydb.cursor()

    query = 'SELECT * FROM student_data WHERE username = %s LIMIT 1;'
    cursor.execute(query,(user),)
    user_id = cursor.fetchone()
    if user_id== None:
        message = 'No Info available.'
        return render_template('profile.html', message=message, username=user, value= base['coordinator'])
    else:
        displayed = [user_id[2], user_id[3], user_id[5], user_id[8], user_id[7], user_id[9], user_id[11], user_id[12]]
        cursor.close()
        cursor_2.execute('''SELECT * FROM uploaded_files WHERE username = %s''', (user))
        result = cursor_2.fetchone()
        if result:
            file = result[2]
            image_data = file
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            photos.append(image_base64)
        return render_template('profile.html',  username=user, displayed=displayed, photos=photos, value= base['coordinator'])


# Display students' data for nonmembers
@app.route('/nonmembers')
def nonmembers():
    cursor = mydb.cursor()
    query = 'SELECT * FROM student_data'
    cursor.execute(query)
    user_id = cursor.fetchall()

    data =[(i[2], i[3], i[5], i[6], i[8] ,i[9], i[11]) for i in user_id]
    cursor.close()
    return render_template('nonmembers.html', data=data)
    
# Display students' data
@app.route('/student')
def student():
    
    username = session['username']
    cursor = mydb.cursor()
    cursor_2 = mydb.cursor()
    query = 'SELECT * FROM student_data'
    cursor.execute(query)
    user_id = cursor.fetchall()

    data =[(i[2], i[3], i[5], i[6], i[8] ,i[9], i[11]) for i in user_id]
    cursor.close()
    return render_template('student_data.html', data=data, username=username, value= base['coordinator'])


# Send mass email
@app.route('/send_email', methods=['GET', 'POST'])
def send_email():
    if request.method == 'POST':
        if session.get('loggedin') and session.get('username') == base['coordinator']:
            subject = request.form['subject']
            body = request.form['body']

            
            approved_users = User.query.filter_by(approved=True).all()

            
            for user in approved_users:
                msg = Message(subject=subject, recipients=[user.email])
                msg.body = body
                mail.send(msg)

            message = 'Email sent to approved users'
            return render_template('profile.html', message=message, username= session['username'], value = base['coordinator'])
        else:
            message = 'Action Not Allowed.'
            return render_template('profile.html', message=message, username= session['username'], value = base['coordinator'])

    return render_template('email.html')


@app.route('/new_members', methods=['GET', 'POST'])
def new_members():
    if request.method == 'POST':
        if session.get('loggedin') and session.get('username') == base['coordinator']:
            subject = request.form['subject']
            body = request.form['body']
            approved_users = User.query.filter_by(approved=False).all()
            for user in approved_users:
                msg = Message(subject=subject, recipients=[user.email])
                msg.body = body
                mail.send(msg)

            message = 'Email sent!'
            return render_template('profile.html', message=message, username= session['username'], value= base['coordinator'])
        else:
            message = 'Action Not Allowed.'
            return render_template('profile.html', message=message, username= session['username'], value= base['coordinator'])

    return render_template('email.html')

# Delete account
@app.route('/delete_account', methods=['POST'])
def delete_account():
    if request.method == 'POST':
        username = session['username']
        user = User.query.filter_by(username=username).first()
        if user and 'username' in session and user.username == session['username']:
            try:
                user.delete()
                session.pop('loggedin',None)
                session.pop('username', None)
                message= 'Account deleted successfully.'
                return render_template('deleted.html', message=message)
            except IntegrityError:
                db.session.rollback()
                flash('Error deleting account.', 'error')
                return redirect(url_for('home'))

    flash('Invalid request.', 'error')
    return redirect(url_for('home'))

# Lougout
@app.route('/logout')
def logout():
    session.pop('loggedin',None)
    session.pop('username', None)
    return render_template('login.html')


# Run dashboard script
@app.route('/reload_2', methods=['GET', 'POST'])
def reload_2():
    if request.method == 'POST':
        subprocess.call(['python', 'dashboard.py'])
    return redirect(url_for('index'))

@app.route('/reload', methods=['GET', 'POST'])
def reload():
    if request.method == 'POST':
        subprocess.call(['python', 'dashboard.py'])
    return redirect(url_for('home'))

# Templates
@app.route('/profile')
def profile():
    username = session['username']
    return render_template('profile.html', username=username, value= base['coordinator'])

@app.route('/add')
def add():
    username= session['username']
    return render_template('user_input.html',  username=username, value= base['coordinator'])

@app.route('/map')
def map():
    return render_template('output.html')

@app.route('/histogram')
def histogram():
    return render_template('histogram.html')

@app.route('/pie_chart')
def pie_chart():
    return render_template('pie_chart.html')

@app.route('/bar_chart')
def bar_chart():
    return render_template('bar_chart.html')

@app.route('/regions')
def regions_chart():
    return render_template('regions_chart.html')

###

if(__name__)== '__main__':
    app.run(host='127.0.0.1', port=8080,debug=True)

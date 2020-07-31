from flask import Flask, render_template, Response, request, redirect
from flask_bcrypt import Bcrypt
import urllib
from json import loads
from camera import VideoCamera
from camboard import VideoCameraBoard
from dbase import Database

# Email validation with Email Validator by Chema JSON API
def validate_email(email):
    # JSON API url and email to validate
    url = 'https://garridodiaz.com/emailvalidator/index.php?email=' + email
    # Parse to url format
    url_parsed = urllib.parse.urlparse(url)
    # Create a request to get the webpage
    req = urllib.request.Request(url_parsed.geturl(), headers={'User-Agent': 'Mozilla/5.0'})

    # Open the webpage handle
    file_handle = urllib.request.urlopen(req)
    # Loads the JSON generated by the API
    # {"valid":false,"message":"No valid email format"}
    data = loads(file_handle.read())
    return data['valid']

# Validate all the data from the registration page
# Creates and returns a dictionary with the errors generated with the data
def validate_register(username, email, password, password_repeat):
    errors = dict()
    # Verifies if the username conatains less than 32 characters
    if len(username) > 32:
        errors['username'] = 'El nombre de usuario debe tener máximo 32 caracteres'

    # Verifies if the password contains more than 8 characters and contains at least one number and one special character
    if len(password) < 8 or not any(c.isalnum() for c in password) or not any(c.isdigit() for c in password):
        errors['password'] = 'La contraseña debe tener al menos 8 caracteres y debe tener al menos un número y un caracter especial'

    # Verifies if both passwords submitted are the same
    if password != password_repeat:
        errors['repeat'] = 'Las dos contraseñas deben ser iguales'

    # Verifies if the email account is already registered
    if database.search_by_email(email):
        errors['email'] = 'Este email ya tiene una cuenta en VedAR'

    # Verifies if the email is valid
    if 'email' not in errors and not validate_email(email):
        errors['email'] = 'El email debe ser válido'
    return errors

# Creates the app
app = Flask(__name__, template_folder="templates")
# Creates a Bcrypt object
bcrypt = Bcrypt(app)

# Initializes the cam with a NoneType value and the database with a new Database() object
cam = None
database = Database()
database.create_tables()

# It is routed to the home page
@app.route('/home')
def index():
    # The cam becomes NoneType
    global cam
    cam = None
    # Renders the home webpage
    return render_template('index.html')

# The GET method routes to the login page
# The POST method verifies the user's data with the one stored in the database
@app.route('/login', methods=['GET', 'POST'])
def login():
    # POST method
    if request.method == 'POST':
        # Get the input from login webpage
        email = request.form['inputEmail']
        password = request.form['inputPassword']

        # Verifies the input in the database
        email_exists, password_s = database.verify_user(email)

        # Creates an errors Dictionary if the email is not found or the password in incorrect
        errors = dict()
        if not email_exists:
            errors['email'] = 'El correo ingresado no ha sido registrado'
        else:
            # Compares the hash of the passwords
            password_correct = bcrypt.check_password_hash(password_s, password)
            if not password_correct:
                errors['password'] = 'Contraseña incorrecta'

        # Verifies if errors were generated
        if errors:
            # Renders the login webpage with the errors
            return render_template('login.html', errors=errors)
        else:
            # Renders the user page
            return redirect('/user/' + email)
    # GET method
    else:
        # Renders the login webpage
        return render_template('login.html')

# The GET method routes to the register page
# The POST method verifies the user's data and stores it in the database
@app.route('/register', methods=['GET', 'POST'])
def register():
    # POST method
    if request.method == 'POST':
        # Get the input from register webpage
        username = request.form['inputUsername']
        institution = request.form['inputInstitution']
        role = request.form['optradio']
        email = request.form['inputEmail']
        password = request.form['inputPassword']
        password_repeat = request.form['inputConfirmPassword']

        # Verifies if all the data is valid
        errors = validate_register(username, email, password, password_repeat)

        # Verifies if errors were generated
        if bool(errors):
            # Renders the register webpage with the errors
            return render_template('register.html', errors=errors)
        else:
            # Hashes the password
            pw_hashed = bcrypt.generate_password_hash(password, 10)
            # Stores the data in the database
            database.create_user(username, email, str(role), institution, pw_hashed)
            # Renders the user page
            return redirect('/user/' + email)
    # GET method
    else:
        # Renders the register webpage
        return render_template('register.html')

# It is routed to the users's account given the email as a parameter to render all the data from the database
@app.route('/user/<email>')
def user(email):
    # The cam becomes NoneType
    global cam
    cam = None
    # Given the email, it recovers all the data of the user in the form of a Dictionary
    user_data = database.search_by_email(email)

    # Renders the user's account with all its data
    return render_template('user.html', user_data=user_data)

# The GET method routes to the users's account configuration page given the email as a parameter to render all the data from the database
# The POST method verifies the user's data and updates it in the database
@app.route('/user/<email>/settings', methods=['GET', 'POST'])
def user_settings(email):
    # Given the email, it recovers all the data of the user in the form of a Dictionary
    user_data = database.search_by_email(email)

    # POST method
    if request.method == 'POST':
        # Get the input from account settings webpage
        username = request.form['inputUsername']
        institution = request.form['inputInstitution']
        role = request.form['optradio']
        about = request.form['inputAbout']

        # If the some data is blank it assigns the one stored in the database
        if username is None:
            username = user_data.username
        if institution is None:
            institution = user_data.institutions
        else:
            institution = institution.strip()
        if role is None:
            role = user_data.role

        # Creates an errors Dictionary if the username is more than 32 characters long
        errors = dict()
        if len(username) > 32:
            errors['username'] = 'El nombre de usuario debe tener máximo 32 caracteres'

        # Verifies if errors were generated
        if errors:
            # Renders the account settings webpage with the user's data and errors
            return render_template('settings.html', user_data=user_data, errors=errors)
        else:
            # Updates the changes in the database
            database.save_changes(email, username, institution, role, about)
            # Renders the user page with the update
            return redirect('/user/' + email)
    # GET method
    else:
        # Renders the account settings webpage with the user's data
        return render_template('settings.html', user_data=user_data)

# The GET method routes to the users's friends page given the email as a parameter to render all the data from the database
# The POST method verifies the friends added and updates it in the database
@app.route('/user/<email>/friends', methods=['GET', 'POST'])
def user_friends(email):
    # Given the email, it recovers all the data of the user and friends in the form of a Dictionaries
    user_data = database.search_by_email(email)
    friends = database.search_friends_by_email(email)

    # POST method
    if request.method == 'POST':
        # Get the input from account friends webpage
        friend_email = request.form['inputEmail']

        errors = database.add_friend(email, friend_email)
        # Verifies if errors were generated
        if errors:
            # Renders the account friend webpage with the user's data and errors
            return render_template('friends.html', user_data=user_data, friends=friends, errors=errors)
        else:
            # Renders the user page with the update
            return redirect('/user/' + email + '/friends')
    else:
        # Renders the account friend webpage with the user's data
        return render_template('friends.html', user_data=user_data, friends=friends)

# The GET method routes to the users's messages page given the email as a parameter to render all the data from the database
# The POST method verifies the messages sent and updates it in the database
@app.route('/user/<email>/friends/send', methods=['GET', 'POST'])
def send_message(email):
    # Given the email, it recovers all the data of the user, friends, and messages in the form of a Dictionaries
    user_data = database.search_by_email(email)
    friends = database.search_friends_by_email(email)
    messages = database.recover_messages(email)

    # POST method
    if request.method == 'POST':
        # Get the input from account messages webpage
        friend_email = request.form['inputEmail']
        message = request.form['inputMessage']

        errors = database.send_message(email, friend_email, message)
        # Verifies if errors were generated
        if errors:
            # Renders the account messages webpage with the user's data and errors
            return render_template('message.html', user_data=user_data, friends=friends, messages=messages, errors=errors)
        else:
            # Renders the success message sent page
            return redirect('/user/' + email + '/friends/send/success')
    else:
        # Renders the account messages webpage with the user's data
        return render_template('message.html', user_data=user_data, friends=friends, messages=messages)

@app.route('/user/<email>/friends/send/success')
def success(email):
    # Renders the success message sent page
    return render_template('success.html', email=email)

# It is routed to the student session
@app.route('/user/<email>/student')
def video(email):
    # The cam becomes a VideoCamera() object
    global cam
    cam = VideoCamera()

    # Adds a new user session to the database
    database.add_session(email)

    # Renders the video session webpage
    return render_template('session.html', email=email)

# It is routed to the teacher session
@app.route('/user/<email>/board')
def board(email):
    # The cam becomes a VideoCameraBoard() object
    global cam
    cam = VideoCameraBoard()

    # Adds a new user session to the database
    database.add_session(email)

    # Renders the video session webpage
    return render_template('session.html', email=email)

# Captures the webcam frame and yields it as an image
def gen(camera):
    while True:
        # Get camera frame
        frame = camera.get_frame()[0]
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

# Captures the webcam processed image and yields it as an image
def gen2(camera):
    while True:
        # Get camera processed image
        processed_image = camera.get_frame()[1]
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + processed_image + b'\r\n\r\n')

# It is routed to the frames generated by the webcam
@app.route('/video_feed')
def video_feed():
    return Response(gen(cam),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# It is routed to the processed images generated by the webcam
@app.route('/image_feed')
def image_feed():
    return Response(gen2(cam),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# When a 404 error (page not found) is generated, it is routed to a personalized page
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html', title='404'), 404

# Initializes a new server at the localhost using the port 5000 and debug mode on
if __name__ == '__main__':
    # defining server ip address and port
    app.run(host='0.0.0.0', port='5000', debug=True)
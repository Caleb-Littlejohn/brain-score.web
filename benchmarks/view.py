from django.views import View
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from .forms import *
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth import get_user_model, login, authenticate, update_session_auth_hash, logout
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from .tokens import account_activation_token
from django.core.mail import EmailMessage
from django.urls import reverse
from urllib.request import Request, urlopen
import requests
import json
import time
import datetime
from .views.index import get_context

User = get_user_model()

# Lookup django convention for this!
#_logger = logging.getLogger(__name__)

class Activate(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except(TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and account_activation_token.check_token(user, token):
            # activate user and login:
            user.is_active = True
            user.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            form = PasswordChangeForm(request.user)

            return HttpResponseRedirect('../../profile/')

        else:
            return HttpResponse('Activation link is invalid!')

    def post(self, request):
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user) # Important, to update the session with the new password
            return HttpResponse('Password changed successfully')

class Signup(View):
    def get(self, request):
        form = SignupForm()
        return render(request, 'benchmarks/signup.html', {'form': form})

    def post(self, request):
        form = SignupForm(request.POST)
        if form.is_valid():
            # Create an inactive user with no password:
            user = form.save()
            user.is_active = False
            to_email = form.cleaned_data.get('email')
            user.save()

            # Send an email to the user with the token:
            mail_subject = 'Activate your account.'
            current_site = get_current_site(request)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = account_activation_token.make_token(user)
            activation_link = "{0}/activate/{1}/{2}".format(current_site, uid, token)
            message = "Hello {0}!\n\nPlease click or paste the following link to activate your account:\n{1}".format(
                user.get_full_name(), activation_link)
            email = EmailMessage(mail_subject, message, to=[to_email])
            email.send()
            context = {"activation_email": False, "password_email": True, 'form': LoginForm}
            return render(request, 'benchmarks/login.html', context)
        elif form.errors:
            context = {'form': form}
            return render(request, 'benchmarks/signup.html', context)
        else:
            context = {'form': LoginForm}
            return render(request, 'benchmarks/login.html', context)

class Login(View):
    def get(self, request):
        form = LoginForm()
        return render(request, 'benchmarks/login.html', {'form': LoginForm})

    def post(self, request):
        form = LoginForm(data=request.POST)
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user is not None:
            login(request, user)
            return render(request, 'benchmarks/profile.html')
        else:
            context = {"Incorrect": True, 'form': form}
            return render(request, 'benchmarks/login.html', context)

class Logout(View):
    def get(self, request):
        logout(request)
        return HttpResponseRedirect('../../')

class Upload(View):
    def get(self, request):
        if str(request.user) == "AnonymousUser":
            return HttpResponseRedirect('../profile/')
        form = UploadFileForm()
        return render(request, 'benchmarks/upload.html', {'form': form})

    def post(self, request):
        if request.user.get_lowest_datefield() < datetime.date.today() - datetime.timedelta(7):

            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                
                json_info = {
                    "model_type": request.POST['model_type'],
                    "name": request.POST['name'],
                    "email": request.user.get_full_name(),
                    "gpu_size": "8000",
                    "type": "zip"
                }

                with open('result.json', 'w') as fp:
                    json.dump(json_info, fp)

                _loggerprint(request.user.get_full_name())

                jenkins_url = "http://braintree.mit.edu:8080"
                auth = ("caleb", "BrownFoxTree")
                job_name = "endpoint_copy"
                request_url = "{0:s}/job/{1:s}/buildWithParameters?TOKEN=trigger2scoreAmodel&email={2:s}".format(
                    jenkins_url,
                    job_name,
                    request.user.get_full_name()
                )

                print(request_url)

                print("Determining next build number")
                current_url = "{0:s}/job/{1:s}/api/json".format(
                        jenkins_url,
                        job_name,
                    )

                job = requests.get(
                    current_url,
                    auth=auth,
                ).json()

                next_build_number = job['nextBuildNumber']
                next_build_url = "{0:s}/job/{1:s}/{2:d}/api/json".format(
                    jenkins_url,
                    job_name,
                    next_build_number,
                )

                params = {"submission.zip": request.FILES['zip_file'], 'submission.config': open('result.json', 'rb')}
                print("Triggering build: {0:s} #{1:d}".format(job_name, next_build_number))
                response = requests.post(request_url, files=params, auth=auth)

                print(response)

                response.raise_for_status()
                print("Job triggered successfully")

                request.user.set_lowest_datefield(datetime.date.today())
                
                return render(request, 'benchmarks/success.html')
            else:
                return HttpResponse("Too many submission attempts")
        else:
            return HttpResponse("Form is invalid")

class Profile(View):
    def get(self, request):
        if str(request.user) == "AnonymousUser":
            form = LoginForm()
            return render(request, 'benchmarks/login.html', {'form': LoginForm})
        else:
            context = get_context(request.user)
            return render(request, 'benchmarks/profile.html', context)

    def post(self, request):
        form = LoginForm(data=request.POST)
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user is not None:
            login(request, user)

            # Currently, there are no model submissions with user fields, so for testing
            # purposes, trying to get the model named "xception" will allow an easy change to the user models.
            
            context = get_context(user) # Change to username once we change the submission model.

            return render(request, 'benchmarks/profile.html', context)
        else:
            context = {"Incorrect": True, 'form': LoginForm}
            return render(request, 'benchmarks/login.html', context)

class Password(View):
    def get(self, request):
        form = PasswordResetForm()
        return render(request, 'benchmarks/password.html', {'form': form})

    def post(self, request):
        form = PasswordResetForm(request.POST)
        username = request.POST["email"]
        if form.is_valid() and User._default_manager.get_by_natural_key(username) != None:
            # Create an inactive user with no password:
            username = request.POST["email"]
            user = User._default_manager.get_by_natural_key(username)
            to_email = username

            # Send an email to the user with the token:
            mail_subject = 'Change Password Request'
            current_site = get_current_site(request)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = account_activation_token.make_token(user)
            activation_link = "{0}/password-change/{1}/{2}".format(current_site, uid, token)
            message = "Hello {0}!\n\nPlease click or paste the following link to change your password:\n{1}".format(
                user.get_full_name(), activation_link)
            email = EmailMessage(mail_subject, message, to=[to_email])
            email.send()
            context = {"activation_email": False, "password_email": True, 'form': LoginForm}
            return render(request, 'benchmarks/login.html', context)
        elif form.errors:
            context = { 'form': form }
            return render(request, 'benchmarks/password.html', context)
        else:
            context = {"activation_email": False, 'password_email': False, 'form': LoginForm}
            return render(request, 'benchmarks/login.html', context)

class ChangePassword(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except(TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        form = ChangePasswordForm(user=user)
        if user is not None and account_activation_token.check_token(user, token):
            # activate user and login:
            form = ChangePasswordForm(user=user)

            return render(request, 'benchmarks/password.html', { 'form': form })

        else:
            return HttpResponse('Password change link is invalid!')

    def post(self, request, uidb64, token):
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except(TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        form = ChangePasswordForm(user=user, data=request.POST)
        if form.is_valid():
            user.set_password(request.POST["new_password1"])
            user.save()
            user.is_active = True
            return HttpResponseRedirect('../../profile/')
        elif form.errors:
            context = { 'form': form }
            return render(request, 'benchmarks/password.html', context)
        else:
            context = {"email": True, 'form': form}
            return render(request, 'benchmarks/password.html', {'form': form})

"""
Feedback Form (email)

class Feedback(View):
    def get(self, request):
        if request.user.is_anonymous:
            return HttpResponseRedirect("../profile")

        form = FeedbackForm(request.POST)
        return render(request, 'benchmarks/feedback.html', {'form': form})

    def post(self, request):
        if request.user.is_anonymous:
            return HttpResponseRedirect("../profile")
        form = FeedbackForm(request.POST)
        if form.is_valid():
            # Send an email to the user with the token:
            mail_subject = request.POST['Subject']
            message = "{0}\n{1}".format(request.user, request.POST['Feedback'])
            email = EmailMessage(mail_subject, message, to=['clittlejohn268@gmail.com'])
            email.send()
            context = {"activation_email": False, "password_email": False, 'form': LoginForm}
            return HttpResponseRedirect("../profile")
        else:
            return HttpResponseRedirect("../profile")"""

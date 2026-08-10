import re
import traceback
import threading
from flask import Flask, Response, current_app, render_template, request, redirect, url_for, session, g, abort, jsonify, flash, send_from_directory
from translations import translate
from flask_mail import Mail, Message
from flask_migrate import Migrate
from sqlalchemy import JSON
import time
import os
import uuid
import json
from auth import login_required
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from firebase_admin import auth
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
import cloudinary
import cloudinary.uploader
from functools import wraps
from firebase_admin import messaging
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError, NotFound
from groq import Groq
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_admin import Admin

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
admin = Admin(name='MediaMission Admin')
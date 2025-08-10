from django.contrib import admin
from .models import Competition, UserProfile, Registration, Team

# Registered model to Django Admin
admin.site.register(Competition)
admin.site.register(UserProfile)
admin.site.register(Registration)
admin.site.register(Team)

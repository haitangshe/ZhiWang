"""ZhiWang URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from retrieve.views import IndexView, Search
from user.views import LoginView, RegisterView, LogoutView

urlpatterns = [
    url(r'^U2FsdGVkX18sI5oUus4o69GtiyYMZliP/', admin.site.urls),
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^login$', LoginView.as_view(), name='login'),
    url(r'^logout', LogoutView.as_view(), name='logout'),

    url(r'^register', RegisterView.as_view(), name='register'),
    url(r'^captcha/', include('captcha.urls')),
    url(r'^retrieve/$', Search.as_view(), name='retrieve'),
    url(r'^retrieve/', include('retrieve.urls', namespace='retrieve')),
]

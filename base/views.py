from django.shortcuts import render, redirect
from django.db.models import Q
from django.http import HttpResponse, HttpRequest
from .models import Room, Topic, Message, User
from django.views import generic
from .forms import RoomForm, MessageForm, UserForm, MyUserCreationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count
# Create your views here.


def home(request: HttpRequest):
    q = request.GET.get('q') if request.GET.get('q') != None else ""
    total_rooms_count = Room.objects.all().count()
    rooms = Room.objects.filter(
        Q(topic__name__icontains=q) |
        Q(name__icontains=q) |
        Q(description=q)
    )
    topics = Topic.objects.all().annotate(
        num_room=Count('room')).order_by('-num_room')[0:5]
    rooms_count = rooms.count()
    room_messages: Message = Message.objects.filter(
        Q(room__topic__name__icontains=q))

    context = {
        'q': q,
        'rooms': rooms,
        'topics': topics,
        'rooms_count': rooms_count,
        'room_messages': room_messages,
        'total_rooms_count': total_rooms_count
    }
    return render(request, 'base/home.html', context)


def room(request: HttpRequest, pk: int):
    room: Room = Room.objects.get(id=pk)
    room_messages: Message = room.message_set.all()
    participants = room.participants.all()

    if request.method == 'POST':
        message: Message = Message.objects.create(
            user=request.user,
            room=room,
            body=request.POST.get('body')
        )
        room.participants.add(request.user)
        return redirect('room', pk=room.id)

    context = {
        'room': room,
        'room_messages': room_messages,
        'participants': participants
    }

    return render(request, 'base/room.html', context)


def userProfile(request: HttpRequest, pk: int):
    user = User.objects.get(id=pk)
    total_rooms_count = Room.objects.all().count()
    rooms = user.room_set.all()
    topics = Topic.objects.all()
    rooms_count = rooms.count()
    room_messages = user.message_set.all()

    context = {
        'user': user,
        'rooms': rooms,
        'topics': topics,
        'rooms_count': rooms_count,
        'room_messages': room_messages,
        'total_rooms_count': total_rooms_count
    }

    return render(request, 'base/profile.html', context)


@login_required(login_url='login')
def createRoom(request: HttpRequest):
    form = RoomForm()
    topics = Topic.objects.all().annotate(
        num_room=Count('room')).order_by('-num_room')

    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)

        room = Room.objects.create(
            host=request.user,
            topic=topic,
            name=request.POST.get('name'),
            description=request.POST.get('description'),

        )
        room.participants.add(request.user)
        return redirect('home')

    context = {'form': form, 'topics': topics}
    return render(request, 'base/room_form.html', context)


@login_required(login_url='login')
def updateRoom(request: HttpRequest, pk: int):
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room)

    if (request.user != room.host):
        return HttpResponse("Only hosts can edit the room.")

    if request.method == "POST":
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)
        room.name = request.POST.get('name')
        room.description = request.POST.get('description')
        room.topic = topic
        room.save()

        return redirect('home')
    context = {'form': form, 'room': room}
    return render(request, 'base/room_form.html', context)


@login_required(login_url='login')
def deleteRoom(request: HttpRequest, pk: int):
    room = Room.objects.get(id=pk)
    if request.method == 'POST':
        room.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj': room})


def loginPage(request: HttpRequest):
    page = 'login'

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
        except:
            messages.error(request, 'User does not exist')

        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Username OR password does not exist')
    context = {'page': page}
    return render(request, 'base/login_register.html', context)


def logoutUser(request: HttpRequest):
    logout(request)
    return redirect('home')


def registerPage(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect('home')

    form = MyUserCreationForm()
    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)

        if form.is_valid():
            user: User = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'An error occured during registration.')

    return render(request, 'base/login_register.html', {'form': form})


@login_required(login_url='login')
def deleteMessage(request: HttpRequest, pk: int):
    message: Message = Message.objects.get(id=pk)

    if request.user != message.user:
        return HttpResponse("You cannot delete the message as you are not the owner.")

    if request.method == 'POST':
        message.delete()
        return redirect('room', pk=message.room.id)

    return render(request, 'base/delete.html', {'obj': message})


"""POST
@login_required(login_url='login')
def updateMessage(request: HttpRequest, pk: int):
    message: Message = Message.objects.get(id=pk)
    form = MessageForm(instance=message)

    if (request.user != message.user):
        return HttpResponse("You are not allowed to edit the message.")

    if request.method == "POST":
        form = MessageForm(request.POST, instance=message)
        if form.is_valid():
            form.save()
            return redirect('room', pk=message.room.id)
    context = {'form': form}
    return render(request, 'base/message_form.html', context)
"""


@login_required(login_url='login')
def updateUser(request: HttpRequest):
    user = request.user
    form = UserForm(instance=user)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile', pk=user.id)

    context = {'form': form}
    return render(request, 'base/update-user.html', context)


def topicPage(request: HttpRequest):
    q = request.GET.get('q') if request.GET.get('q') != None else ""
    topics = Topic.objects.filter(Q(name__icontains=q)).annotate(
        num_room=Count("room")).order_by('-num_room')
    total_rooms_count = Room.objects.all().count()
    context = {'topics': topics,
               'total_rooms_count': total_rooms_count, 'q': q}
    return render(request, 'base/topics.html', context)


def activityPage(request: HttpRequest):
    room_messages: Message = Message.objects.all()[0:3]
    context = {'room_messages': room_messages}
    return render(request, 'base/activity.html', context)

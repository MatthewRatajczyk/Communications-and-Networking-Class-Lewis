import aioconsole
import asyncio
import click
import requests, requests_oauthlib, sys
import json
from chat_server import ChatServer
from chat_client import (
    ChatClient,
    NotConnectedError,
    LoginConflictError,
    LoginError
)

async def display_msgs(chat_client):
    while True:
        msg = await chat_client.get_user_msg()
        print('\n\n\t\tRECEIVED MESSAGE: {}'.format(msg))


async def handle_user_input(chat_client, loop):
    uname = False
    lname = ''
    rooms = []
    auth_obj,Logedin = init_auth()
    if Logedin == False:
        print("You were unable to Login to Twitter T commands dissabled")
    followers = []
    follow = False

    while True:
        print('\n\n')
        print('< 1 > close connection and quits')
        print('< 2 > list logged-in users')
        print('< 3 > login')
        print('< 4 > list rooms')
        print('< 5 > post message')
        print('< 6 > create a room')
        print('< 7 > join a room')
        print('< 8 > leave a room')
        if Logedin == True:
            print('*** Twitter Commands ***')
            print('< T1 > List Direct Messages')
            print('< T2 > List Followers')
            print('< T3 > Send Direct Message')

        print('\tchoice: ', end='', flush=True)

        command = await aioconsole.ainput()
        if command == '1':
            # disconnect
            try:
                chat_client.disconnect()
                print('disconnected')
                loop.stop()
            except NotConnectedError:
                print('client is not connected ...')
            except Exception as e:
                print('error disconnecting {}'.format(e))

        elif command == '2':  # list registered users
            users = await chat_client.lru()
            print('logged-in users: {}'.format(', '.join(users)))

        elif command == '3':
            login_name = await aioconsole.ainput('enter login-name: ')
            try:
                await chat_client.login(login_name)
                print(f'logged-in as {login_name}')
                uname = True
                lname = login_name

            except LoginConflictError:
                print('login name already exists, pick another name')
            except LoginError:
                print('error logging in, try again')

        elif command == '4':
            try:
                rooms = await chat_client.lrooms()
                for room in rooms:
                    print('\n\t\troom name ({}), owner ({}): {}'.format(room['name'], room['owner'], room['description']))

            except Exception as e:
                print('error getting rooms from server {}'.format(e))

        elif command == '5':
            try:
                myinput = await aioconsole.ainput('Enter 1 for user message or 2 for room message: ')
                if myinput == '1':
                    user_name = await aioconsole.ainput('What user would you like to send a message to: ')
                    user_msg = await aioconsole.ainput('enter your message: ')
                    await chat_client.private_message(user_name, user_msg, lname)
                    pass
                elif myinput == '2':
                    user_room = await aioconsole.ainput('what room would you like to send a message to: ')
                    user_message = await aioconsole.ainput('enter your message: ')
                    await chat_client.post(user_message, user_room, lname)
                else:
                    print('Invalid input')

            except Exception as e:
                print('error posting message {}'.format(e))

        elif command == '6':
            if uname:
                try:
                    print('Room may not be larger than 10 characters long,')
                    print('No special characters or spaces allowed!')
                    proom = await aioconsole.ainput('Enter your room name: ')
                    roomlen = len(proom)
                    print("Your room length is: ", roomlen)
                    char = set(' @!#$%^&*()_+={}|[]?/.,<>;":')
                    if any((c in char) for c in proom):
                        print("Found an illegal character")
                    else:
                        desc = await aioconsole.ainput('Describe the room: ')
                        make_response = await chat_client.make_room(proom, lname, desc)
                        rooms.append(proom)
                        print("{}".format(make_response))
                except Exception as e:
                    print(e)
            else:
                print("You need to have a username to use this function")

        elif command == '7':
            flag = True
            if uname:
                try:
                    jroom = await aioconsole.ainput('What room would you like to join: ')
                    for k in rooms:
                        if k == jroom:
                            flag = False
                            break
                    if flag:
                        jroom_response = await chat_client.join_room(jroom)
                        print('{}'.format(jroom_response))
                        rooms.append(jroom)
                    else:
                        print('You are already in this room')

                except Exception as e:
                    print(e)
            else:
                print("You need to have a username to use this function")
        elif command == '8':
            if uname:
                try:
                    r_room = await aioconsole.ainput('What room would you like to leave: ')
                    r_room_response = await chat_client.leave_room(r_room)
                    print('{}'.format(r_room_response))
                except Exception as e:
                    print(e)
            else:
                print("You need to have a username to use this function")
        #Twitter Commands
        elif command == 'T1':
            if uname:
                toBePrinted = await chat_client.list_dms(auth_obj)
                print(toBePrinted)
            else:
                print("You need to have a username to use this function")
        elif command == 'T2':
            if uname:
                # toBePrinted = await chat_client.get_followers(auth_obj)
                # print(toBePrinted)
                print("Followers:")
                for msg in await chat_client.get_followers(auth_obj):
                    print(msg)
                    msg1 = {'name': msg[0],
                            'id': msg[1],
                            'screen_name': msg[2]}
                    followers.append(msg1)
                follow = True

            else:
                print("You need to have a username to use this function")
        elif command == 'T3':
            if uname:
                # Message = await aioconsole.ainput('What is your message: ')
                # toBePrinted = await chat_client.send_dm(auth_obj, Message)
                # print(toBePrinted)
                if follow:
                    found = False
                    user_id = 0
                    try:
                        print("Followers:")
                        for r in followers:
                            print(r['name'])
                        print('Select a user to send message to: ')
                        user = await aioconsole.ainput()
                        print("User selected: {}".format(user))
                        for r in followers:
                            if r['name'] == user:
                                found = True
                                user_id = r['id']
                                break
                        if found:
                            print("User located, Enter your message: ")
                            msg = await aioconsole.ainput()
                            await chat_client.send_dm(auth_obj, msg, user_id)
                            print("Message sent")

                        else:
                            print("User not located, Please check your spelling and followers again.")

                    except Exception as e:
                        print(e)
                else:
                    print('Check your followers first')
            else:
                print("You need to have a username to use this function")




def verify_credentials(auth_obj):
    url = "https://api.twitter.com/1.1/account/verify_credentials.json"
    response = requests.get(url, auth=auth_obj)
    return response.status_code == 200

def init_auth():
    Logedin = False
    consumer_key = ""
    consumer_secret = ""
    access_token = ""
    access_secret = ""


    auth_obj = requests_oauthlib.OAuth1(consumer_key,
                                        consumer_secret,
                                        access_token,
                                        access_secret)
    if verify_credentials(auth_obj):
        print('Validated credentials')
        Logedin = True
        return auth_obj, Logedin
    else:
        print('Credentials not validated')
        return auth_obj, Logedin

@click.group()
def cli():
    pass


@cli.command(help="run chat client")
@click.argument("host")
@click.argument("port", type=int)
def connect(host, port):
    chat_client = ChatClient(ip=host, port=port)
    loop = asyncio.get_event_loop()

    loop.run_until_complete(chat_client._connect())

    # display menu, wait for command from user, invoke method on client
    asyncio.ensure_future(handle_user_input(chat_client=chat_client, loop=loop))
    asyncio.ensure_future(display_msgs(chat_client=chat_client))

    loop.run_forever()


@cli.command(help='run chat server')
@click.argument('port', type=int)
def listen(port):
    click.echo('starting chat server at {}'.format(port))
    chat_server = ChatServer(port=port)
    chat_server.start()


if __name__ == '__main__':
    cli()
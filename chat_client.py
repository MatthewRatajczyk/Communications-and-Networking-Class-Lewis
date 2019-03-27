import asyncio
import threading
import requests, requests_oauthlib, sys
import json

class NotConnectedError(Exception):
    pass


class LoginError(Exception):
    pass


class LoginConflictError(Exception):
    pass


class ChatClientProtocol(asyncio.Protocol):
    def __init__(self):
        self._pieces = []
        self._responses_q = asyncio.Queue()
        self._user_messages_q = asyncio.Queue()

    def connection_made(self, transport: asyncio.Transport):
        self._transport = transport

    def data_received(self, data):
        self._pieces.append(data.decode('utf-8'))

        if ''.join(self._pieces).endswith('$'):
            protocol_msg = ''.join(self._pieces).rstrip('$')

            if protocol_msg.startswith('/MSG '):
                user_msg = protocol_msg.lstrip('/MSG')
                asyncio.ensure_future(self._user_messages_q.put(user_msg))
            else:
                asyncio.ensure_future(self._responses_q.put(''.join(self._pieces).rstrip('$')))

            self._pieces = []

    def connection_lost(self, exc):
        self._transport.close()


class ChatClient:
    def __init__(self, ip, port):
        self._ip = ip
        self._port = port
        self._connected = False

    def disconnect(self):
        if not self._connected:
            raise NotConnectedError()

        self._transport.close()

    async def _connect(self):
        try:
            loop = asyncio.get_event_loop()
            self._transport, self._protocol = await loop.create_connection(
                lambda: ChatClientProtocol(),
                self._ip,
                self._port)

            self._connected = True
            print('connected to chat server')

        except ConnectionRefusedError:
            print('error connecting to chat server - connection refused')

        except TimeoutError:
            print('error connecting to chat server - connection timeout')

        except Exception as e:
            print('error connecting to chat server - fatal error')

    def connect(self):
        loop = asyncio.get_event_loop()
        try:
            asyncio.ensure_future(self._connect())

            loop.run_forever()
        except Exception as e:
            print(e)
        finally:
            print('{} - closing main event loop'.format(threading.current_thread().getName()))
            loop.close()

    async def lru(self):
        self._transport.write('/lru $'.encode('utf-8'))
        # await for response message from server
        lru_response = await self._protocol._responses_q.get()

        # unmarshel into list of registered users
        # /lru omari, nick, tom
        users = lru_response.lstrip('/lru ').split(', ')

        # filter out any Nones or empty strings
        users = [u for u in users if u and u != '']

        return users

    async def login(self, login_name):
        self._transport.write('/login {}$'.format(login_name).encode('utf-8'))
        login_response = await self._protocol._responses_q.get()
        success = login_response.lstrip('/login ')

        if success == 'already exists':
            raise LoginConflictError()

        elif success != 'success':
            raise LoginError()

    async def lrooms(self):
        # expected response format:
        # /lroom public&system&public room\nroom1, omari, room to discuss chat service impl

        self._transport.write('/lrooms $'.encode('utf-8'))
        lrooms_response = await self._protocol._responses_q.get()

        lines = lrooms_response.lstrip('/lrooms ').split('\n')

        rooms = []
        for line in lines:
            room_attributes = line.split('&')
            rooms.append({'name': room_attributes[0], 'owner': room_attributes[1], 'description': room_attributes[2]})

        return rooms

    async def post(self, msg, room, lname):
        # post to a room:
        # /post public&hello everyone
        self._transport.write('/post {}&{}&{}$'.format(lname.strip() ,room.strip(), msg.strip()).encode('utf-8'))

    async def private_message(self, user_name, message, lname):
        self._transport.write('/msg {}&{}&{}$'.format(lname.strip(), user_name.strip(), message.strip()).encode('utf-8'))

    async def get_user_msg(self):
        return await self._protocol._user_messages_q.get()

    async def make_room(self,room_name,user_name,description):
        self._transport.write('/make {}&{}&{}$'.format(room_name,user_name,description).encode('utf-8'))
        make_room_response = await self._protocol._responses_q.get()
        return make_room_response

    async def join_room(self, room):
        self._transport.write('/join {}$'.format(room).encode('utf-8'))
        join_room_response = await self._protocol._responses_q.get()
        return join_room_response

    async def leave_room(self, room):
        self._transport.write('/leave {}$'.format(room).encode('utf-8'))
        leave_room_response = await self._protocol._responses_q.get()
        return leave_room_response

    async def list_dms(self, auth_obj):
        url = "https://api.twitter.com/1.1/direct_messages/events/list.json"
        response = requests.get(url, auth=auth_obj)
        response.raise_for_status()
        r_json = json.loads(response.text)
        #print(r_json)
        messages = [(e['id'], e['message_create']['message_data']['text']) for e in r_json['events']]
        return messages

    async def send_dm(self, auth_obj, message, user_id):
        url = "https://api.twitter.com/1.1/direct_messages/events/new.json"
        payload = {"event":
                       {"type": "message_create",
                        "message_create":
                            {"target": {"recipient_id": user_id},
                             "message_data": {"text": message}
                             }
                        }
                   }

        response = requests.post(url, data=json.dumps(payload), auth=auth_obj)
        response.raise_for_status()
        return json.loads(response.text)

    async def get_followers(sefl, auth_obj):
        url = "https://api.twitter.com/1.1/followers/list.json"
        response = requests.get(url=url, auth=auth_obj)
        response.raise_for_status()
        r_json = json.loads(response.text)
        # Message = [(r['screen_name'], r['name']) for r in r_json['users']]
        Message = [(r['name'], r['id'], r['screen_name']) for r in r_json['users']]
        return Message

if __name__ == '__main__':
    LOCAL_HOST = '127.0.0.1'
    PORT = 8080

    loop = asyncio.get_event_loop()
    chat_client = ChatClient(LOCAL_HOST, PORT)
    asyncio.ensure_future(chat_client._connect())

    chat_client.disconnect()
import asyncio


class ChatServerProtocol(asyncio.Protocol):
    # master dict {transport: {'remote': ('127.0.0.1', 76678), 'login-name': 'omari', 'rooms': [public, room1]}
    clients = {}
    rooms = [{'name': 'public',
              'owner': 'system',
              'description': 'The public room which acts as broadcast, all logged-in users are in public room by default'}
             ]

    def __init__(self):
        self._pieces = []

    def fileLogger(writeToFile):
        toFile = writeToFile
        f = open("ServerLogs.txt", "a")
        f.write(toFile)
        f.close()

    def _handle_command(self):
        command = ''.join(self._pieces)
        self._pieces = []

        if command.startswith('/lru'):
            # get list of registered users
            lru = [r['login-name'] for r in ChatServerProtocol.clients.values() if r['login-name']]
            response = '/lru '
            for user in lru:
                response += (f'{user}, ')

            response.rstrip(', ')
            response = ''.join([response, '$'])
            self._transport.write(response.encode('utf-8'))




        elif command.startswith('/login '):
            # TODO: check if login-name already exists
            # TODO: what to do when already logged-in

            login_name = command.lstrip('/login').rstrip('$').strip()

            all_login_names = [v['login-name'] for v in ChatServerProtocol.clients.values()]
            if login_name in all_login_names:
                response = '/login already exists$'
            else:
                client_record = ChatServerProtocol.clients[self._transport]
                client_record['login-name'] = login_name
                response = '/login success$'

            self._transport.write(response.encode('utf-8'))

            #Were going to write this to a file
            writeToFinal = 'logged-in users: {}\n'.format(login_name)
            ChatServerProtocol.fileLogger(writeToFinal)

        elif command.startswith('/lrooms '):
            # response format
            # /lroom public&system&public room\nroom1&omari&room to discuss chat service impl$

            room_msgs = ['{}&{}&{}'.format(r['name'], r['owner'], r['description']) for r in ChatServerProtocol.rooms]
            response = '/lrooms {}$'.format('\n'.join(room_msgs))
            self._transport.write(response.encode('utf-8'))

        elif command.startswith('/post '):
            # expected request format: /post public&hello everyone
            lname, room, msg = command.lstrip('/post').rstrip('$').split('&')

            transports = [k for k, v in ChatServerProtocol.clients.items() if room.strip() in v['rooms']]
            print(transports)
            print('COMPLETED')
            msg_to_send = '/MSG FROM ROOM: {}\n\t\t{}: {} \nPRESS ENTER TO CONTINUE$'.format(room, lname, msg)
            for transport in transports:
                transport.write(msg_to_send.encode('utf-8'))

            #Were going to write this to a file
            writeToFinal = 'Message posted to Room: {} from user:{} Message: {}\n'.format(room, lname, msg)
            ChatServerProtocol.fileLogger(writeToFinal)


        elif command.startswith('/msg '):
            lname, receiver_name, msg = command.lstrip('/msg ').rstrip('$').split('&')
            transports = [k for k, v in ChatServerProtocol.clients.items() if receiver_name.strip() in v['login-name']]
            print(transports)
            print('COMPLETED')
            msg_to_send = '/MSG FROM: {}: {}$'.format(lname, msg)
            for transport in transports:
                transport.write(msg_to_send.encode('utf-8'))

        elif command.startswith('/make '):
            dupliroom = False
            rname, lname, description = command.lstrip('/make ').rstrip('$').split('&')
            for r in ChatServerProtocol.rooms:
                if r['name'] == rname:
                    dupliroom = True
            if dupliroom == False:
                msg2 = {'name': rname,
                        'owner': lname,
                        'description': description}
                ChatServerProtocol.rooms.append(msg2)
                ChatServerProtocol.clients.get(self._transport).get('rooms').append(rname)
                msg = '\nRoom Created!$'
                self._transport.write(msg.encode('utf-8'))
                writeToFinal = 'Room {} was created by user{} the Description:{}\n'.format(rname, lname, description)
                ChatServerProtocol.fileLogger(writeToFinal)
            else:
                msg = '\nRoom already exists!\n Try another name!$'
                self._transport.write(msg.encode('utf-8'))

        elif command.startswith('/join '):
            found = False
            room = command.lstrip('/join ').rstrip('$')
            for x in ChatServerProtocol.rooms:
                if x['name'] == room:
                    found = True
                    break
            if found:
                client_record = ChatServerProtocol.clients[self._transport]
                mylist = []
                for x in client_record['rooms']:
                    mylist.append(x)
                mylist.append(room)
                client_record['rooms'] = mylist
                msg = 'You have joined the room$'
                self._transport.write(msg.encode('utf-8'))
            else:
                msg = 'This room does not exist, please check your spelling$'
                self._transport.write(msg.encode('utf-8'))

        elif command.startswith('/leave '):
            rname = command.lstrip('/leave ').rstrip('$')
            exists = False
            client_record = ChatServerProtocol.clients[self._transport]
            mylist = []
            for x in client_record['rooms']:
                if x == rname:
                    exists = True
                else:
                    mylist.append(x)
            if exists:
                client_record['rooms'] = mylist
                msg = 'Removed from room$'
                self._transport.write(msg.encode('utf-8'))
            else:
                msg = 'Room does not exist$'
                self._transport.write(msg.encode('utf-8'))

        elif command.startswith('/TwitterDM '):
            lname, receiver_name, msg = command.lstrip('/msg ').rstrip('$').split('&')
            transports = [k for k, v in ChatServerProtocol.clients.items() if receiver_name.strip() in v['login-name']]
            print(transports)
            print('COMPLETED')
            msg_to_send = '/MSG FROM: {}: {}$'.format(lname, msg)
            for transport in transports:
                transport.write(msg_to_send.encode('utf-8'))

    def connection_made(self, transport: asyncio.Transport):
        """Called on new client connections"""
        self._remote_addr = transport.get_extra_info('peername')
        print('[+] client {} connected.'.format(self._remote_addr))
        self._transport = transport
        ChatServerProtocol.clients[transport] = {'remote': self._remote_addr, 'login-name': None, 'rooms': ['public']}

    def data_received(self, data):
        """Handle data"""
        self._pieces.append(data.decode('utf-8'))
        if ''.join(self._pieces).endswith('$'):
            self._handle_command()

    def connection_lost(self, exc):
        """remote closed connection"""
        ChatServerProtocol.clients.pop(self._transport)
        print('[-] lost connectio to {}'.format(ChatServerProtocol.clients[self._transport]))
        self._transport.close()


class ChatServer:
    LOCAL_HOST = '0.0.0.0'

    def __init__(self, port):
        self._port: int = port

    def listen(self):
        """start listening"""
        pass

    def start(self):
        """start"""
        loop = asyncio.get_event_loop()
        server_coro = loop.create_server(lambda: ChatServerProtocol(),
                                         host=ChatServer.LOCAL_HOST,
                                         port=self._port)

        loop.run_until_complete(server_coro)
        loop.run_forever()


if __name__ == '__main__':
    chat_server = ChatServer(port=8080)
    chat_server.start()
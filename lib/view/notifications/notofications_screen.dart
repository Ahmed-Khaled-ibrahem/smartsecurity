import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:smartsecurity/common/confirmation_dialog.dart';
import 'package:smartsecurity/controller/appCubit/app_cubit.dart';
import 'package:smartsecurity/services/firebase_auth.dart';
import 'package:smartsecurity/services/firebase_real_time.dart';
import '../../services/get_it.dart';
import '../messaging/send_notification.dart';

class NotoficationsScreen extends StatefulWidget {
  const NotoficationsScreen({super.key});

  @override
  State<NotoficationsScreen> createState() => _NotoficationsScreenState();
}

class _NotoficationsScreenState extends State<NotoficationsScreen> {
  String selectedTab = 'Inbox'; // Default tab
  Map zonedMessages = {};
  Map inboxMessages = {};
  Map outboxMessages = {};

  @override
  void initState() {
    super.initState();
    zonedMessages = getIt<FirebaseRealTimeDB>().zonedMessages;
  }

  filterMessages() {
    String myID = getIt<FirebaseAuthRepo>().currentUser!.uid.toString();
    bool isAdmin = getIt<FirebaseRealTimeDB>().isAdmin();
    String myZone = getIt<AppCubit>().allStaff[myID]['zone'] ?? '';

    zonedMessages.forEach((zoneName, messages) {
      messages.forEach((messageID, messageMap) {
        if (isOutbox(messageMap)) {
          messageMap['zone'] = zoneName;
          outboxMessages[messageID] = messageMap;
        } else {
          if (isAdmin) {
            messageMap['zone'] = zoneName;
            inboxMessages[messageID] = messageMap;
          } else {
            if (myZone.trim() == zoneName.trim()) {
              messageMap['zone'] = zoneName;
              inboxMessages[messageID] = messageMap;
            }
          }
        }
      });
    });
  }

  bool isOutbox(Map messageMap) {
    return messageMap['sender_id'] ==
        getIt<FirebaseAuthRepo>().currentUser!.uid.toString();
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(
      bottomNavigationBar: GestureDetector(
        onTap: () {
          Navigator.push(
              context,
              MaterialPageRoute(
                  builder: (context) => const SendNotification()));
        },
        child: const Card(
            child: Padding(
                padding: EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [Text('Send New Message'), Icon(Icons.send)],
                ))),
      ),
      appBar: AppBar(
        title: const Text('Messaging'),
        actions: [
          Builder(builder: (context) {
            if (!getIt<FirebaseRealTimeDB>().isAdmin()) {
              return Container();
            }
            return IconButton(
              icon: const Icon(Icons.delete),
              onPressed: () async {
                bool? result = await showConfirmationDialog(context,
                    title: 'Delete',
                    content: 'Are you sure you want to delete all notifications?');
                if (result == true) {
                  getIt<FirebaseRealTimeDB>().deleteAllNotifications();
                  Navigator.pop(context);
                }
              },
            );
          }),
        ],
      ),
      body: BlocBuilder<AppCubit, AppState>(
        builder: (context, state) {
          zonedMessages = getIt<FirebaseRealTimeDB>().zonedMessages;
          filterMessages();
          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(15),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Expanded(
                      flex: selectedTab == 'Inbox' ? 2 : 1,
                      child: TextButton(
                        style: TextButton.styleFrom(
                          backgroundColor: selectedTab != 'Outbox'
                              ? Colors.lightBlueAccent
                              : Colors.grey.withOpacity(0),
                        ),
                        onPressed: () {
                          setState(() {
                            selectedTab = 'Inbox';
                          });
                        },
                        child: Text(
                          'Inbox',
                          style: TextStyle(
                            color: selectedTab == 'Inbox'
                                ? Theme.of(context).primaryColor
                                : Colors.grey,
                          ),
                        ),
                      ),
                    ),
                    Expanded(
                      flex: selectedTab == 'Inbox' ? 1 : 2,
                      child: TextButton(
                        style: TextButton.styleFrom(
                          backgroundColor: selectedTab == 'Outbox'
                              ? Colors.lightBlueAccent
                              : Colors.grey.withOpacity(0),
                        ),
                        onPressed: () {
                          setState(() {
                            selectedTab = 'Outbox';
                          });
                        },
                        child: Text(
                          'Outbox',
                          style: TextStyle(
                            color: selectedTab == 'Outbox'
                                ? Theme.of(context).primaryColor
                                : Colors.grey,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Builder(builder: (context) {
                if (selectedTab == 'Inbox') {
                  return listMessages(inboxMessages);
                }
                return listMessages(outboxMessages);
              })
            ],
          );
        },
      ),
    );
  }

  Widget listMessages(Map messages) {
    return Expanded(
      child: ListView.builder(
        itemCount: messages.length,
        itemBuilder: (context, index) {
          var message = messages.values.toList()[index];
          return Card(
            margin: const EdgeInsets.all(10),
            child: Padding(
              padding: const EdgeInsets.all(10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 15),
                    child: Text(message['zone'] ?? ''),
                  ),
                  const Divider(),
                  ListTile(
                    title: Text(message['content']),
                    subtitle: Text('By : '+message['sender_name']),
                    trailing: Text(message['time'].split(' ')[0] +'\n'+ message['time'].split(' ')[1]),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

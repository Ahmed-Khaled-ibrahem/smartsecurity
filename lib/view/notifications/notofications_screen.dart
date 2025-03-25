import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:smartsecurity/common/confirmation_dialog.dart';
import 'package:smartsecurity/controller/appCubit/app_cubit.dart';
import 'package:smartsecurity/services/firebase_auth.dart';
import 'package:smartsecurity/services/firebase_real_time.dart';
import '../../services/get_it.dart';

class NotoficationsScreen extends StatefulWidget {
  const NotoficationsScreen({super.key});

  @override
  State<NotoficationsScreen> createState() => _NotoficationsScreenState();
}

class _NotoficationsScreenState extends State<NotoficationsScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete),
            onPressed: () async {
              bool? result = await showConfirmationDialog(context, title: 'Delete', content: 'Are you sure you want to delete all notifications?');
              if (result == true) {
                getIt<FirebaseRealTimeDB>().deleteAllNotifications();
                Navigator.pop(context);
              }
            },
          )
        ],
      ),
      body: BlocBuilder<AppCubit, AppState>(
        builder: (context, state) {
          var appCubit = getIt<AppCubit>();
          Map staff = appCubit.allStaff;
          Map? myData = staff[getIt<FirebaseAuthRepo>().currentUser!.uid.toString()];

          if (myData == null) {
            return  const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Icon(
                    Icons.notifications_none_outlined,
                    size: 64,
                  ),
                  Text('error')
                ],
              ),
            );
          }
          Map notifications = myData['notifications'] ?? {};

          if (notifications.isEmpty) {
            return  const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Icon(
                    Icons.notifications_none_outlined,
                    size: 64,
                  ),
                  Text('No Notifications')
                ],
              ),
            );
          }

          return  ListView(
            children:
              notifications.entries.map((entry) {
                return ListTile(
                  title: Text(entry.value),
                  subtitle: Text(entry.key),
                );
              }).toList()
            ,
          );
        },
      ),
    );
  }
}

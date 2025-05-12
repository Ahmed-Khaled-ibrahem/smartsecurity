import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:smartsecurity/controller/appCubit/app_cubit.dart';
import 'package:smartsecurity/controller/theme_bloc/theme_state.dart';
import 'package:smartsecurity/services/theme_service.dart';
import '../../common/confirmation_dialog.dart';
import '../../controller/theme_bloc/theme_bloc.dart';
import '../../controller/theme_bloc/theme_event.dart';
import '../../services/firebase_auth.dart';
import '../../services/firebase_real_time.dart';
import '../../services/get_it.dart';
import '../messaging/send_notification.dart';
import '../permetions/pernitions_screen.dart';
import '../users/users_screen.dart';

class MyDrawer extends StatefulWidget {
  const MyDrawer({super.key});

  @override
  State<MyDrawer> createState() => _MyDrawerState();
}

class _MyDrawerState extends State<MyDrawer> {
  @override
  Widget build(BuildContext context) {
    return Drawer(
      child: BlocBuilder<AppCubit, AppState>(
        builder: (context, state) {
          return SafeArea(
            child: BlocBuilder<ThemeBloc, ThemeState>(
              builder: (context, state) {
                return Column(children: <Widget>[
                  const SizedBox(
                    height: 30,
                  ),
                  ListTile(
                    leading: const CircleAvatar(
                      backgroundImage: NetworkImage(
                          'https://cdn-icons-png.flaticon.com/512/219/219988.png'),
                    ),
                    title: Text(
                      getIt<FirebaseAuthRepo>().currentUser?.displayName ?? '',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(
                      getIt<FirebaseAuthRepo>().currentUser?.email ?? '',
                      style: const TextStyle(
                          fontWeight: FontWeight.w400, fontSize: 10),
                    ),
                  ),
                  const Divider(
                    indent: 10,
                    endIndent: 10,
                    color: Colors.orange,
                  ),
                  const SizedBox(
                    height: 30,
                  ),
                  const Row(
                    children: [
                      SizedBox(
                        width: 20,
                      ),
                      Text(
                        "Theme",
                        style: TextStyle(fontSize: 20),
                      ),
                    ],
                  ),
                  ListTile(
                    leading: const Icon(Icons.light_mode),
                    title: const Text('Light'),
                    tileColor:
                        state.isDark ? null : ThemeService.lightSelections,
                    onTap: () => lightTheme(context),
                  ),
                  ListTile(
                    leading: const Icon(Icons.dark_mode),
                    title: const Text('Dark'),
                    onTap: () => darkTheme(context),
                    tileColor:
                        state.isDark ? ThemeService.darkSelections : null,
                  ),
                  // ListTile(
                  //   leading: const Icon(Icons.phone_android),
                  //   title: const Text('Device Theme'),
                  //   onTap: () => deviceTheme(context),
                  // ),
                  const SizedBox(
                    height: 30,
                  ),

                  Builder(builder: (context) {
                    if (getIt<FirebaseRealTimeDB>().isAdmin()) {
                      return Column(
                        children: [
                          const Divider(
                            indent: 10,
                            endIndent: 10,
                            color: Colors.orange,
                          ),
                          ListTile(
                            leading: const Icon(Icons.roundabout_left_outlined),
                            title: const Text('Permissions'),
                            onTap: () {
                              Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (context) =>
                                          const PernitionsScreen()));
                            },
                          ),
                          ListTile(
                            leading: const Icon(Icons.message),
                            title: const Text('Messaging'),
                            onTap: () {
                              Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (context) =>
                                          const SendNotification()));
                            },
                          ),
                          ListTile(
                            leading: const Icon(
                                Icons.supervised_user_circle_rounded),
                            title: const Text('Staff'),
                            onTap: () {
                              Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (context) =>
                                          const UsersScreen()));
                            },
                          ),
                        ],
                      );
                    }
                    return Container();
                  }),
                  const Divider(
                    indent: 10,
                    endIndent: 10,
                    color: Colors.orange,
                  ),
                  ListTile(
                    onTap: () async {
                      bool result = await showConfirmationDialog(context,
                          title: 'Logout',
                          content: 'Are you sure you want to logout?');
                      if (result) {
                        getIt<FirebaseAuthRepo>().signOut();
                      }
                    },
                    leading: const Icon(Icons.door_back_door_outlined),
                    title: const Text('Logout'),
                  ),
                  const Spacer(),
                  Builder(builder: (context) {
                    if (getIt<AppCubit>().isAdmin) {
                      return const Padding(
                        padding: EdgeInsets.all(8.0),
                        child: Column(
                          children: [
                            Icon(
                              Icons.verified,
                              size: 40,
                              color: Colors.green,
                            ),
                            Text(
                              'admin account',
                              style: TextStyle(
                                  fontSize: 16, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                      );
                    }
                    return Container();
                  })
                ]);
              },
            ),
          );
        },
      ),
    );
  }

  void deviceTheme(context) {
    Brightness brightness =
        SchedulerBinding.instance.platformDispatcher.platformBrightness;
    BlocProvider.of<ThemeBloc>(context).add(ChangeTheme(
        useDeviceTheme: true, isDark: brightness == Brightness.dark));
    // getIt<NavigationService>().goBack();
  }

  void lightTheme(context) {
    BlocProvider.of<ThemeBloc>(context)
        .add(const ChangeTheme(useDeviceTheme: false, isDark: false));
    // getIt<NavigationService>().goBack();
  }

  void darkTheme(context) {
    BlocProvider.of<ThemeBloc>(context)
        .add(const ChangeTheme(useDeviceTheme: false, isDark: true));
    // getIt<NavigationService>().goBack();
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:smartsecurity/controller/appCubit/app_cubit.dart';
import '../../common/confirmation_dialog.dart';
import '../../model/permissions.dart';
import '../../services/get_it.dart';

class PernitionsScreen extends StatefulWidget {
  const PernitionsScreen({super.key});

  @override
  State<PernitionsScreen> createState() => _PernitionsScreenState();
}

class _PernitionsScreenState extends State<PernitionsScreen> {
  Map localPermissions = {};

  @override
  void initState() {
    super.initState();
    var cubit = getIt<AppCubit>();
    Map? onlinePermissions = cubit.onlinePermissions;
    getIt<PermissionsRepo>().addOnlinePermissions(onlinePermissions);
  }

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<AppCubit, AppState>(
      builder: (context, state) {
        var cubit = getIt<AppCubit>();
        var devices = cubit.devices;
        List<CardPermission> localPermissions =
            getIt<PermissionsRepo>().getAllCardsPermissions() ?? [];

        return Scaffold(
          appBar: AppBar(
            title: const Text('Permissions'),
            actions: [
              IconButton(
                icon: const Icon(Icons.restart_alt),
                onPressed: () async {
                  bool result = await showConfirmationDialog(context,
                      title: 'Reset',
                      content: 'Do you want to reset permissions?');
                  if (result) {}
                },
              )
            ],
          ),
          bottomNavigationBar: BottomAppBar(
            child: ElevatedButton(
              child: const Text('Save'),
              onPressed: () {
                getIt<PermissionsRepo>()
                    .saveLocalPermissions(localPermissions);
                Navigator.pop(context);
              },
            ),
          ),
          body: ListView.builder(
              itemCount: localPermissions.length,
              itemBuilder: (context, index) {
                return ExpansionTile(
                  title: Text(localPermissions[index].cardName),
                  children: devices.map((device) {
                    return ListTile(
                      title: Text(device.name),
                      trailing: Builder(builder: (context) {
                        List<Permission> permissions =
                            localPermissions[index].permissions.permissions;
                        List<String> filteredPermissions =
                            permissions.map((permission) {
                          return permission.espId;
                        }).toList();

                        if (filteredPermissions.contains(device.id)) {
                          return Checkbox(
                            value: permissions[
                                    filteredPermissions.indexOf(device.id)]
                                .isAllowed,
                            onChanged: (value) {
                              localPermissions[index]
                                  .permissions
                                  .permissions
                                  .where((element) => element.espId == device.id)
                                  .first
                                  .setIsAllowed(!localPermissions[index]
                                  .permissions
                                  .permissions
                                  .where((element) => element.espId == device.id)
                                  .first
                                  .isAllowed);
                              setState(() {

                              });
                              // cubit.updateDevice(element);
                            },
                          );
                        }
                        localPermissions[index].permissions.permissions.add(
                            Permission(
                                espId: device.id,
                                espName: device.name,
                                isAllowed: true));
                        return Checkbox(
                          value: localPermissions[index]
                              .permissions
                              .permissions
                              .where((element) => element.espId == device.id)
                              .first
                              .isAllowed,
                          onChanged: (value) {
                            localPermissions[index]
                                .permissions
                                .permissions
                                .where((element) => element.espId == device.id)
                                .first
                                .setIsAllowed(!localPermissions[index]
                                .permissions
                                .permissions
                                .where((element) => element.espId == device.id)
                                .first
                                .isAllowed);
                            setState(() {

                            });
                            // cubit.updateDevice(element);
                          },
                        );
                      }),
                    );
                  }).toList(),
                );
              }),
        );
      },
    );
  }
}

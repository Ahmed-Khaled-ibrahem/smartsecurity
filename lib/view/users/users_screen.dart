import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:smartsecurity/controller/appCubit/app_cubit.dart';
import 'package:smartsecurity/services/firebase_real_time.dart';
import 'package:smartsecurity/services/get_it.dart';

class UsersScreen extends StatefulWidget {
  const UsersScreen({super.key});

  @override
  State<UsersScreen> createState() => _UsersScreenState();
}

class _UsersScreenState extends State<UsersScreen> {
  final staffData = getIt<AppCubit>().allStaff;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        FocusManager.instance.primaryFocus?.unfocus();
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Staff'),
        ),
        body: BlocBuilder<AppCubit, AppState>(
          builder: (context, state) {
            return ListView(
              children: staffData.entries.map((entry) {
                Map staff = entry.value;
                final controller =
                TextEditingController(text: staff['zone'].toString());
                return ExpansionTile(
                  title: Text(staff['name'].toString()),
                  subtitle: Text(staff['email'].toString()),
                  children: [
                    ListTile(
                      title: TextFormField(
                        controller: controller,
                        decoration: const InputDecoration(
                          labelText: 'Zone',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      leading: const Icon(Icons.meeting_room_rounded),
                      trailing: ElevatedButton(
                        onPressed: () {
                          getIt<FirebaseRealTimeDB>().updateZone(
                              entry.key.toString(), controller.text.trim());
                          Navigator.pop(context);
                          getIt<AppCubit>().readData();
                        },
                        style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.green,
                            foregroundColor: Colors.white),
                        child: const Text('Update'),
                      ),
                    )
                  ],
                );
              }).toList(),
            );
          },
        ),
      ),
    );
  }
}

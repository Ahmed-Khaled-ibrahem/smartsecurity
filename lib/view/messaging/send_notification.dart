import 'package:flutter/material.dart';
import 'package:smartsecurity/controller/appCubit/app_cubit.dart';
import '../../services/firebase_auth.dart';
import '../../services/firebase_real_time.dart';
import '../../services/get_it.dart';

class SendNotification extends StatefulWidget {
  const SendNotification({super.key});

  @override
  State<SendNotification> createState() => _SendNotificationState();
}

class _SendNotificationState extends State<SendNotification> {
  final controller = TextEditingController();
  final devices = getIt<AppCubit>().devices;
  String? selected;
  var isAdmin = getIt<FirebaseRealTimeDB>().isAdmin();

  @override
  void initState() {
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        FocusManager.instance.primaryFocus?.unfocus();
      },
      child: Scaffold(
          appBar: AppBar(
            title: const Text('Send Message'),
          ),
          body: ListView(
            children: [
              Builder(
                builder: (context) {
                  if(!isAdmin){
                    var appCubit = getIt<AppCubit>();
                    Map staff = appCubit.allStaff;
                    Map? myData = staff[getIt<FirebaseAuthRepo>().currentUser!.uid.toString()];
                    String userZone = myData?['zone'] ?? '';
                    getZones().forEach((element) {
                      if(element.trim() == userZone.trim()) {
                        selected = element.trim();
                      }
                    });

                    if(selected != null){
                      return  Card(
                          margin: const EdgeInsets.all(10),
                          child: Padding(
                            padding: const EdgeInsets.all(15),
                            child: Text(selected!),
                          ));
                    }
                    return const Card(
                      margin: EdgeInsets.all(10),
                      child: Padding(
                        padding: EdgeInsets.all(15),
                        child: Text('Unavailable Zone'),
                    ));
                  }
                  return Padding(
                    padding: const EdgeInsets.all(15),
                    child: DropdownButtonFormField<String>(
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        labelText: 'Choose Zone',
                      ),
                      items: getZones().map((String value) {
                        return DropdownMenuItem<String>(
                          value: value,
                          child: Text(value),
                        );
                      }).toList(),
                      onChanged: (String? newValue) {
                        selected = newValue;
                      },
                    ),
                  );
                }
              ),
              Padding(
                padding: const EdgeInsets.all(15),
                child: TextFormField(
                  controller: controller,
                  minLines: 6,
                  maxLines: 15,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    labelText: 'Message',
                  ),
                ),
              )
            ],
          ),
          floatingActionButton: FloatingActionButton(
            child: const Icon(Icons.send),
            onPressed: () {
              if (selected == null) {
                ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Please Select Zone')));
                return;
              }
              if (controller.text.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Please Write Message')));
                return;
              }
              // getIt<AppCubit>().storeNotification(selected!, controller.text);
              getIt<FirebaseRealTimeDB>().addMessage(controller.text, selected!);
              Navigator.pop(context);
              // getIt<AppCubit>().refresh();
            },
          )),
    );
  }

  List<String> getZones() {
    final d = devices.where((element) => element.name != "unknown").toList();
    final names = d.map((e) => e.name).toList();
    return names;
  }
}

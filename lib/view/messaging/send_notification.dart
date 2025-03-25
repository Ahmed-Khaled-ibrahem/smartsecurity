import 'package:flutter/material.dart';
import 'package:smartsecurity/controller/appCubit/app_cubit.dart';

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

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        FocusManager.instance.primaryFocus?.unfocus();
      },
      child: Scaffold(
          appBar: AppBar(
            title: const Text('Send Notification'),
          ),
          body: ListView(
            children: [
              Padding(
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
              getIt<AppCubit>().storeNotification(selected!, controller.text);
              Navigator.pop(context);
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

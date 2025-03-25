import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:smartsecurity/controller/appCubit/app_cubit.dart';
import '../../common/confirmation_dialog.dart';
import '../../model/device.dart';
import '../../services/firebase_real_time.dart';
import '../../services/get_it.dart';

class EditDevice extends StatefulWidget {
  EditDevice(this.device, {super.key});

  Device device;

  @override
  State<EditDevice> createState() => _EditDeviceState();
}

class _EditDeviceState extends State<EditDevice> {
  TextEditingController nameController = TextEditingController();
  TextEditingController capacityController = TextEditingController();

  int selectedIndex = 0;
  String selectedType = 'room';
  GlobalKey<FormState> formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    nameController.text = widget.device.name;
    capacityController.text = widget.device.capacity.toString();
    selectedType = widget.device.type;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Edit Device'),
      ),
      body: GestureDetector(
        onTap: () {
          FocusManager.instance.primaryFocus?.unfocus();
        },
        child: SingleChildScrollView(
          child: BlocBuilder<AppCubit, AppState>(
            builder: (context, state) {
              var appCubit = getIt<AppCubit>();
              var devices = appCubit.devices;

              return Column(
                children: [
                  Card(
                    margin: const EdgeInsets.all(10),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          const Text('Device ID '),
                          Text(widget.device.id),
                        ],
                      ),
                    ),
                  ),
                  formFields(devices),
                  TextButton(
                      onPressed: () async {
                        bool result = await showConfirmationDialog(context,
                            content: 'Are you sure you want to delete this device',
                            title: 'Delete Alert');
                        if (result) {
                          await getIt<FirebaseRealTimeDB>().deleteData(widget.device.id);
                          Navigator.pop(context);
                        }
                      },
                      child: const Text(
                        'Delete Device',
                        style: TextStyle(color: Colors.red),
                      ))
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  Widget formFields(devices) {
    return Form(
      key: formKey,
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Column(children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              const Text('Type '),
              SegmentedButton<String>(
                segments: const [
                  ButtonSegment(value: 'room', label: Text("Zone")),
                  ButtonSegment(value: 'gate', label: Text("Gate")),
                ],
                selected: {selectedType},
                onSelectionChanged: (newSelection) {
                  setState(() {
                    selectedType = newSelection.first;
                  });
                },
              ),
            ],
          ),
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: TextFormField(
              controller: nameController,
              validator: (value) => value!.isEmpty ? 'Enter name' : null,
              decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  icon: Icon(Icons.developer_board_rounded),
                  labelText: 'Name'),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: TextFormField(
              controller: capacityController,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              validator: (value) => value!.isEmpty ? 'Enter capacity' : null,
              decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  icon: Icon(Icons.all_inclusive),
                  labelText: 'Capacity'),
            ),
          ),
          const SizedBox(
            height: 50,
          ),
          ElevatedButton(
              onPressed: () async {
                if (formKey.currentState!.validate()) {
                  var device = Device(
                      id: widget.device.id,
                      name: nameController.text,
                      // cards: widget.device.cards,
                      type: selectedType,
                      capacity: int.parse(capacityController.text));

                  getIt<FirebaseRealTimeDB>().updateData(device);
                  await getIt<AppCubit>().refresh();
                  Navigator.pop(context);
                }
              },
              child: const SizedBox(
                  width: double.maxFinite, child: Center(child: Text('Save'))))
        ]),
      ),
    );
  }
}

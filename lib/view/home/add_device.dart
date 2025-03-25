import 'package:carousel_slider/carousel_slider.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:smartsecurity/controller/appCubit/app_cubit.dart';
import '../../model/device.dart';
import '../../services/firebase_real_time.dart';
import '../../services/get_it.dart';

class AddDevice extends StatefulWidget {
  const AddDevice({super.key});

  @override
  State<AddDevice> createState() => _AddDeviceState();
}

class _AddDeviceState extends State<AddDevice> {
  TextEditingController nameController = TextEditingController();
  TextEditingController capacityController = TextEditingController();

  int selectedIndex = 0;
  String selectedType = 'room';
  GlobalKey<FormState> formKey = GlobalKey<FormState>();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Add Device'),
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
              List<Device> needsConfiguration = devices
                  .where((element) => element.name == "unknown")
                  .toList();
              return Column(
                children: [
                  stateCard(devices),
                  needsConfiguration.isEmpty
                      ? const Padding(
                          padding: EdgeInsets.all(60),
                          child: Column(
                            children: [
                              Icon(
                                Icons.done,
                                size: 64,
                              ),
                              Text(
                                'There is no devices needs configuration',
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),
                        )
                      : Column(
                          children: [
                            const Text('Device ID'),
                            deviceSliding(devices),
                            formFields(devices),
                          ],
                        ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  Widget stateCard(List<Device> devices) {
    List<Device> needsConfiguration =
        devices.where((element) => element.name == "unknown").toList();
    return Card(
      margin: const EdgeInsets.all(10),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Online devices'),
              Text(
                devices.length.toString(),
                style: const TextStyle(color: Colors.blue),
              ),
            ],
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Needs Configuration'),
              Text(
                needsConfiguration.length.toString(),
                style: const TextStyle(color: Colors.red),
              ),
            ],
          ),
        ]),
      ),
    );
  }

  Widget deviceSliding(devices) {
    List<Device> needsConfiguration =
        devices.where((element) => element.name == "unknown").toList();
    return CarouselSlider(
      options: CarouselOptions(
        height: 70,
        viewportFraction: 0.7,
        enlargeCenterPage: true,
        enableInfiniteScroll: false,
        autoPlay: false,
        onPageChanged: (positon, reason) {
          selectedIndex = positon;
        },
      ),
      items: needsConfiguration.map((device) {
        return Container(
          margin: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.purple,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Center(
              child:
                  Text(device.id, style: const TextStyle(color: Colors.white))),
        );
      }).toList(),
    );
  }

  Widget formFields(devices) {
    List<Device> needsConfiguration =
        devices.where((element) => element.name == "unknown").toList();

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
                if (needsConfiguration.isEmpty) {
                  return;
                }
                if (formKey.currentState!.validate()) {
                  var device = Device(
                      id: needsConfiguration[selectedIndex].id,
                      name: nameController.text,
                      // cards: [],
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

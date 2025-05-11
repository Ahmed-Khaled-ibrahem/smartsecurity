import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:gauge_indicator/gauge_indicator.dart';
import 'package:smartsecurity/model/device.dart';
import 'package:smartsecurity/services/firebase_real_time.dart';
import 'package:smartsecurity/services/get_it.dart';
import 'package:smartsecurity/view/home/drawer.dart';
import 'package:syncfusion_flutter_charts/charts.dart';
import '../../controller/appCubit/app_cubit.dart';
import '../../model/unauthorized_model.dart';
import '../../services/firebase_auth.dart';
import '../notifications/notofications_screen.dart';
import 'add_device.dart';
import 'edit_device.dart';

class Home extends StatefulWidget {
  const Home({super.key});

  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  bool isPortrait = false;
  bool isAvailable = false;

  @override
  Widget build(BuildContext context) {
    isPortrait = (MediaQuery.of(context).orientation == Orientation.portrait);

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "GuardTag",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.message),
            onPressed: () {
              // showToast('Alert','666 is not allowed in ffff');
              Navigator.push(
                  context,
                  MaterialPageRoute(
                      builder: (context) => const NotoficationsScreen()));
            },
          )
        ],
      ),
      drawer: const MyDrawer(),
      body: Padding(
        padding: const EdgeInsets.all(8.0),
        child: BlocBuilder<AppCubit, AppState>(
          builder: (context, state) {
            return Builder(builder: (context) {
              if (isPortrait) {
                // Portrait
                return Column(
                  children: [
                    summaryCard(),
                    roomsCards(),
                    Builder(builder: (context) {
                      if (getIt<FirebaseRealTimeDB>().isAdmin()) {
                        return addDevice(context);
                      } else {
                        return availableWidget();
                      }
                      return Container();
                    })
                  ],
                );
              }
              // landscape
              return Row(
                children: [
                  SizedBox(
                      width: MediaQuery.of(context).size.width / 2.5,
                      child: summaryCard()),
                  roomsCards(),
                  Builder(builder: (context) {
                    if (getIt<FirebaseRealTimeDB>().isAdmin()) {
                      return addDevice(context);
                    } else {
                      return availableWidget();
                    }
                    return Container();
                  })
                ],
              );
            });
          },
        ),
      ),
    );
  }

  Widget summaryCard() {
    var appCubit = getIt<AppCubit>();
    Map staff = appCubit.allStaff;
    Map? myData = staff[getIt<FirebaseAuthRepo>().currentUser!.uid.toString()];
    String userZone = myData?['zone'] ?? '';

    return BlocBuilder<AppCubit, AppState>(
      builder: (context, state) {
        var appCubit = getIt<AppCubit>();
        var devices = appCubit.devices;
        var thereIsGate =
            appCubit.devices.any((element) => element.type == "gate");
        if (!thereIsGate) {
          return const Card(
              child: Center(
            child: Padding(
              padding: EdgeInsets.all(8.0),
              child: Text('Gate is not configured yet'),
            ),
          ));
        }

        Device gateDevice =
            appCubit.devices.firstWhere((element) => element.type == "gate");
        if (userZone.trim() != gateDevice.name.trim() &&
            !getIt<FirebaseRealTimeDB>().isAdmin()) {
          return Container();
        }

        List<ChartData> _chartData = getChartData(devices);

        var totalCapacity =
            devices.map((element) => element.capacity).reduce((a, b) => a + b);

        return Stack(
          children: [
            Card(
              child: Column(
                children: [
                  SizedBox(
                    height: isPortrait
                        ? MediaQuery.of(context).size.height * 0.3
                        : MediaQuery.of(context).size.height * 0.7,
                    child: SfCircularChart(
                      palette: _chartData.map((e) => e.color).toList(),
                      annotations: <CircularChartAnnotation>[
                        CircularChartAnnotation(
                          widget: Text(
                            gateDevice.inside.toString(),
                            style: TextStyle(
                                fontSize: isPortrait ? 20 : 50,
                                fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                      title: ChartTitle(
                          text: gateDevice.name,
                          alignment: ChartAlignment.near,
                          borderWidth: 5,
                          textStyle: const TextStyle(
                              fontSize: 15, fontWeight: FontWeight.w800)),
                      legend: Legend(
                          isVisible: true,
                          legendItemBuilder: (dynamic data, dynamic series,
                              dynamic point, int index) {
                            DoughnutSeries<ChartData, String> s = series;
                            double percentage = point.y;
                            return SizedBox(
                              width: isPortrait
                                  ? MediaQuery.of(context).size.width * 0.4
                                  : MediaQuery.of(context).size.width * 0.3,
                              child: Column(
                                children: [
                                  Row(
                                    children: [
                                      Expanded(child: Text(point.x)),
                                      Text("${percentage.toStringAsFixed(0)}%"),
                                    ],
                                  ),
                                  LinearProgressIndicator(
                                    value: percentage / 100,
                                    color: s.dataSource?[index].color,
                                    backgroundColor: Colors.grey,
                                  ),
                                ],
                              ),
                            );
                          },
                          overflowMode: isPortrait
                              ? LegendItemOverflowMode.none
                              : LegendItemOverflowMode.wrap,
                          position: isPortrait
                              ? LegendPosition.right
                              : LegendPosition.bottom),
                      series: <DoughnutSeries<ChartData, String>>[
                        DoughnutSeries<ChartData, String>(
                          dataSource: _chartData,
                          xValueMapper: (ChartData data, _) => data.category,
                          yValueMapper: (ChartData data, _) => data.value,
                          dataLabelSettings: const DataLabelSettings(
                              isVisible: false,
                              labelPosition: ChartDataLabelPosition.inside),
                          explode: true,
                          innerRadius: isPortrait ? "70" : "80%",
                        ),
                      ],
                    ),
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      const Text(
                        'Total Capacity',
                        style: TextStyle(
                            fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      SizedBox(
                        width: MediaQuery.of(context).size.width * 0.35,
                        // height: 50,
                        child: AnimatedRadialGauge(
                          duration: const Duration(seconds: 1),
                          curve: Curves.elasticOut,
                          value:
                              (gateDevice.inside / totalCapacity.toDouble()) *
                                      100 +
                                  7,
                          axis: GaugeAxis(
                            min: 0,
                            max: 107,
                            degrees: 150,
                            style: const GaugeAxisStyle(
                              thickness: 15,
                              background: Color(0xFFDFE2EC),
                              segmentSpacing: 1,
                              blendColors: true,
                              cornerRadius: Radius.circular(20),
                            ),
                            pointer: GaugePointer.circle(
                              radius: 10,
                              position: const GaugePointerPosition.center(),
                              color: Colors.black.withOpacity(0),
                            ),
                            progressBar: const GaugeProgressBar.rounded(
                                color: Color(0xFFffcf6d),
                                gradient: GaugeAxisGradient(colors: [
                                  Color(0xFFffcf6d),
                                  Color(0xFFff0000),
                                ])),
                          ),
                          builder: (context, child, value) => RadialGaugeLabel(
                            value: totalCapacity.toDouble(),
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: isPortrait ? 18 : 25,
                            ),
                          ),
                        ),
                      ),
                    ],
                  )
                ],
              ),
            ),
            Positioned(
              right: 15,
              top: 15,
              child: Builder(builder: (context) {
                if (!getIt<FirebaseRealTimeDB>().isAdmin()) {
                  return Container();
                }
                return InkWell(
                  onTap: () {
                    Navigator.push(
                        context,
                        MaterialPageRoute(
                            builder: (context) => EditDevice(
                                  gateDevice,
                                )));
                  },
                  child: const Icon(
                    Icons.mode_edit_rounded,
                  ),
                );
              }),
            ),
          ],
        );
      },
    );
  }

  List<ChartData> getChartData(List<Device> devices) {
    List<Device> labelDevices =
        devices.where((element) => element.name != "unknown").toList();
    return labelDevices.map((element) {
      return ChartData(element.name, element.inside.toDouble(),
          Colors.primaries[Random().nextInt(Colors.primaries.length)]);
    }).toList();
  }

  Widget roomsCards() {
    return BlocBuilder<AppCubit, AppState>(
      builder: (context, state) {
        var appCubit = getIt<AppCubit>();
        var devices = appCubit.devices
            .where((element) => element.type == "room")
            .toList();

        return Expanded(
          child: GridView.count(
            crossAxisCount: 1,
            padding: const EdgeInsets.all(5),
            mainAxisSpacing: 10,
            crossAxisSpacing: 10,
            childAspectRatio: 2.6,
            children: devices.isEmpty
                ? [
                    const Center(
                        child: Text('There is no configured rooms yet')),
                  ]
                : [
                    for (int i = 0; i < devices.length; i++)
                      roomCard(i, context, devices)
                  ],
          ),
        );
      },
    );
  }

  Widget roomCard(index, context, List<Device> devices) {
    var appCubit = getIt<AppCubit>();
    Map staff = appCubit.allStaff;
    Map? myData = staff[getIt<FirebaseAuthRepo>().currentUser!.uid.toString()];
    String userZone = myData?['zone'] ?? '';
    var currentDeviceName = devices[index].name;
    var staffCount = 0;
    var staffAvailableCount = 0;
    staff.forEach((key, value) {
      if (value['zone'].trim() == currentDeviceName.trim()) {
        staffCount++;
        if( value['available'] == true){
          staffAvailableCount++;
        }
      }
    });
    if (userZone.trim() != devices[index].name.trim() &&
        !getIt<FirebaseRealTimeDB>().isAdmin()) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(5),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.lock,
                size: 40,
                color: Colors.red,
              ),
              Text(
                'You are not allowed to access this zone',
                style: TextStyle(fontWeight: FontWeight.w300),
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                maxLines: 4,
              ),
            ],
          ),
        ),
      );
    }

    return Card(
      color: Theme.of(context).primaryColor,
      margin: const EdgeInsets.all(0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          Card(
            margin: const EdgeInsets.all(1),
            child: Padding(
              padding: const EdgeInsets.all(8.0),
              child: Row(
                children: [
                  Expanded(
                    child: Stack(
                      children: [
                        Center(
                          child: Column(
                              // mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Image.asset(
                                  "assets/rfid.png",
                                  scale: 15,
                                ),
                                Text(
                                  devices[index].name,
                                  softWrap: true,
                                  maxLines: 3,
                                  textAlign: TextAlign.center,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ]),
                        ),
                        Positioned(
                          left: 8,
                          top: 8,
                          child: Builder(builder: (context) {
                            if (!getIt<FirebaseRealTimeDB>().isAdmin()) {
                              return Container();
                            }
                            return InkWell(
                                onTap: () {
                                  Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                        builder: (context) => EditDevice(
                                          devices[index],
                                        ),
                                      ));
                                },
                                child: const Icon(
                                  Icons.edit,
                                  size: 20,
                                ));
                          }),
                        ),
                      ],
                    ),
                  ),
                  VerticalDivider(
                    color: Colors.grey.withOpacity(0.5),
                    endIndent: 10,
                    indent: 10,
                    width: 20,
                  ),
                  Expanded(
                    child: AnimatedRadialGauge(
                      duration: const Duration(seconds: 1),
                      curve: Curves.elasticOut,
                      value: (devices[index].inside /
                                  devices[index].capacity.toDouble()) *
                              100 +
                          7,
                      axis: GaugeAxis(
                        min: 0,
                        max: 107,
                        degrees: 210,
                        style: const GaugeAxisStyle(
                          thickness: 15,
                          background: Color(0xFFDFE2EC),
                          segmentSpacing: 1,
                          blendColors: true,
                          cornerRadius: Radius.circular(20),
                        ),
                        pointer: GaugePointer.circle(
                          radius: 10,
                          position: const GaugePointerPosition.center(),
                          color: Colors.black.withOpacity(0),
                        ),
                        progressBar: const GaugeProgressBar.rounded(
                            color: Color(0xFFffcf6d),
                            gradient: GaugeAxisGradient(colors: [
                              Color(0xFFffcf6d),
                              Color(0xFFff0000),
                            ])),
                      ),
                      builder: (context, child, value) => Wrap(
                        children: [
                          RadialGaugeLabel(
                            value: devices[index].capacity.toDouble(),
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: isPortrait ? 18 : 25,
                            ),
                          ),
                          Center(
                            child: Text(
                              'Capacity',
                              textAlign: TextAlign.center,
                              style: TextStyle(fontSize: isPortrait ? 8 : 14),
                            ),
                          )
                        ],
                      ),
                    ),
                  ),
                  VerticalDivider(
                    color: Colors.grey.withOpacity(0.5),
                    endIndent: 10,
                    indent: 10,
                    width: 20,
                  ),
                  Expanded(
                    child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Image.asset(
                            "assets/people.png",
                            scale: 10,
                          ),
                          Text(
                            devices[index].inside.toString(),
                            style: const TextStyle(
                                fontWeight: FontWeight.w900, fontSize: 16),
                          ),
                        ]),
                  ),
                ],
              ),
            ),
          ),
           Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 5),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.people, color: Colors.amberAccent,size: 15,),
                    const SizedBox(width: 5),
                    const Text('Staff : ',
                        style: TextStyle(fontSize: 10,fontWeight: FontWeight.w900, color: Colors.amberAccent)),
                    Text(staffCount.toString(), style: const TextStyle(fontSize: 10,fontWeight: FontWeight.w900, color: Colors.amberAccent)),
                  ],
                ),
                Row(
                  children: [
                    const Icon(Icons.block, color: Colors.tealAccent,size: 15,),
                    const SizedBox(width: 5),
                    const Text('Unauthorized : ',
                        style: TextStyle(fontSize: 10,fontWeight: FontWeight.w900, color: Colors.tealAccent)),
                    Builder(
                        builder: (context) {
                          int counter = 0;
                          List<UnAuthorizedModel> unAuthorizedDevices = getIt<AppCubit>().unAuthorizedDevices;

                          devices[index].cards?.forEach((cardi) {
                            unAuthorizedDevices.where((e) => e.cardId == cardi.id).forEach((element) {
                              if(element.zoneId == devices[index].id){
                                counter+= 1;
                              }
                            });
                          });

                          return Text(counter.toString(), style: const TextStyle(fontSize: 10,fontWeight: FontWeight.w900, color: Colors.tealAccent));
                        }
                    ),],
                ),
                Row(
                  children: [
                    const Icon(Icons.people, color: Color(0xFF00FF00),size: 15,),
                    const SizedBox(width: 5),
                    const Text('Available : ',
                        style: TextStyle(fontSize: 10,fontWeight: FontWeight.w900, color: Color(0xFF00FF00))),
                    Text(staffAvailableCount.toString(), style: const TextStyle(fontSize: 10,fontWeight: FontWeight.w900, color: Color(0xFF00FF00))),
                  ],
                ),


              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget addDevice(BuildContext context) {
    return Card(
      child: GestureDetector(
        onTap: () {
          Navigator.push(context,
              MaterialPageRoute(builder: (context) => const AddDevice()));
        },
        child: Container(
          decoration: const BoxDecoration(),
          child: Center(
            child: Padding(
              padding: isPortrait
                  ? const EdgeInsets.symmetric(vertical: 20)
                  : const EdgeInsets.symmetric(horizontal: 20),
              child: const Icon(Icons.add),
            ),
          ),
        ),
      ),
    );
  }

  Widget availableWidget() {
    var appCubit = getIt<AppCubit>();
    Map staff = appCubit.allStaff;
    Map? myData = staff[getIt<FirebaseAuthRepo>().currentUser!.uid.toString()];
    bool available = myData?['available'] ?? false;

    return Card(
      color: available ? Colors.green : Colors.redAccent,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 2),
        child:
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(available ? 'Available' : 'Unavailable'),
          Switch(
            value: available,
            onChanged: (val) {
              // setState(() {
              available = val;
              getIt<FirebaseRealTimeDB>().updateAvailable(
                  getIt<FirebaseAuthRepo>().currentUser!.uid.toString(), val);
              // });
            },
            activeColor: Colors.white,
          )
        ]),
      ),
    );
  }
}

class ChartData {
  final String category;
  final double value;
  final Color color;

  ChartData(this.category, this.value, this.color);
}

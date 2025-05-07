import 'package:equatable/equatable.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:smartsecurity/model/device.dart';
import 'package:smartsecurity/services/get_it.dart';
import 'package:smartsecurity/services/toast.dart';
import '../../model/permissions.dart';
import '../../services/firebase_real_time.dart';
part 'app_state.dart';

class AppCubit extends Cubit<AppState> {
  AppCubit() : super(AppInitial());

  List<Device> devices = [];
  Map onlinePermissions = {};
  List<String> lastNotifiedCardsIDs = [];
  bool isAdmin = false;
  Map allStaff = {};
  Map<String, int> unAuthorizedDevicesCounter = {};

  void init() async {
    debugPrint("init");
    readData();
    readPermissions();
    getIt<FirebaseRealTimeDB>().listenToChange();
  }

  Future refresh() async {
    await readData();
    print("refreshing");
    state is Refresh ? emit(RefreshExtend()) : emit(Refresh());
  }

  Future readData() async {
    devices = await getIt<FirebaseRealTimeDB>().getData();
    isAdmin = await getIt<FirebaseRealTimeDB>().isAdmin();
    allStaff = await getIt<FirebaseRealTimeDB>().getAllUsers();
  }

  Future readPermissions() async {
    onlinePermissions =
        await getIt<FirebaseRealTimeDB>().getOnlinePermissions();
  }

  void checkPermissions() async {
    await Future.delayed(const Duration(seconds: 1));

    devices.forEach((esp) {
      esp.cards?.forEach((card) {
        if (card.state == 'in') {
          if (lastNotifiedCardsIDs.contains(card.id)) {
            return;
          }

          List<CardPermission> allCardsPermissions =
              getIt<PermissionsRepo>().allCardsPermissions;

          allCardsPermissions.forEach((cardPermission) {
            if (cardPermission.cardId == card.id) {
              cardPermission.permissions.permissions
                  .forEach((permissionDevice) {
                if (permissionDevice.espId == esp.id) {
                  if (!permissionDevice.isAllowed) {
                    showToast('Alert',
                        '${cardPermission.cardName} is not allowed in ${esp.name}');
                    unAuthorizedDevicesCounter[cardPermission.cardId] = unAuthorizedDevicesCounter[cardPermission.cardId] ?? 0 + 1;
                    print('----------------');
                    print(unAuthorizedDevicesCounter);
                    lastNotifiedCardsIDs.add(card.id);
                    refresh();
                  }
                }
              });
            }
          });
        } else {
          lastNotifiedCardsIDs.removeWhere((element) => element == card.id);
        }
      });
    });
  }

  checkCapacity() async {
    devices.forEach((esp) {
      print(esp.capacity );
      print(esp.inside );
      if (esp.capacity <= esp.inside) {
        showToast('Alert', '${esp.name} is full, ${esp.inside} people are inside');
      }
    });
  }

  void storeNotification(String zone, String message) {
    allStaff.forEach((key, value) {
      if (zone == value['zone']) {
        getIt<FirebaseRealTimeDB>().addNotification(key, message);
      }
    });
  }
}

import 'package:equatable/equatable.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:smartsecurity/model/device.dart';
import 'package:smartsecurity/services/get_it.dart';
import 'package:smartsecurity/services/toast.dart';
import '../../model/permissions.dart';
import '../../model/unauthorized_model.dart';
import '../../services/firebase_real_time.dart';
part 'app_state.dart';

class AppCubit extends Cubit<AppState> {
  AppCubit() : super(AppInitial());

  List<Device> devices = [];
  Map onlinePermissions = {};
  List<String> lastNotifiedCardsIDs = [];
  bool isAdmin = false;
  Map allStaff = {};
  List<UnAuthorizedModel> unAuthorizedDevices = [];

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
    for (var esp in devices) {
      esp.cards?.forEach((card) {
        if (card.state == 'in') {
          if (lastNotifiedCardsIDs.contains(card.id)) {
            return;
          }
          List<CardPermission> allCardsPermissions =
              getIt<PermissionsRepo>().allCardsPermissions;

          for (var cardPermission in allCardsPermissions) {
            if (cardPermission.cardId == card.id) {
              for (var permissionDevice in cardPermission.permissions.permissions) {
                if (permissionDevice.espId == esp.id) {
                  if (!permissionDevice.isAllowed) {

                    if(isAdmin){
                      showToast('Alert',
                          '${cardPermission.cardName} is not allowed in ${esp.name}');
                    }

                    UnAuthorizedModel m = UnAuthorizedModel(
                      zoneId: esp.id,
                      cardId: cardPermission.cardId,
                    );

                    bool found = false;
                    for (var element in unAuthorizedDevices) {
                      if(element.zoneId == m.zoneId && element.cardId == m.cardId){
                        found = true;
                      }
                    }

                    if(!found){
                      unAuthorizedDevices.add(m);
                    }

                    lastNotifiedCardsIDs.add(card.id);
                    refresh();
                  }
                }
              }
            }
          }
        } else {
          lastNotifiedCardsIDs.removeWhere((element) => element == card.id);
          unAuthorizedDevices.removeWhere((element) => element.cardId == card.id && element.zoneId == esp.id);
          refresh();
        }
      });
    }
  }

  checkCapacity() async {
    for (var esp in devices) {
      if (esp.capacity <= esp.inside) {
        showToast('Alert', '${esp.name} is full, ${esp.inside} people are inside');
      }
    }
  }

  void storeNotification(String zone, String message) {
    allStaff.forEach((key, value) {
      if (zone == value['zone']) {
        getIt<FirebaseRealTimeDB>().addNotification(key, message);
      }
    });
  }
}

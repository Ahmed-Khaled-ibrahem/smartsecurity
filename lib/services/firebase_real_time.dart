import 'package:firebase_database/firebase_database.dart';
import 'package:intl/intl.dart';
import 'package:smartsecurity/services/get_it.dart';
import 'package:smartsecurity/services/toast.dart';
import '../controller/appCubit/app_cubit.dart';
import '../model/device.dart';
import 'firebase_auth.dart';

class FirebaseRealTimeDB {
  final _database = FirebaseDatabase.instance.ref();
  String currentMail = '';
  Map zonedMessages = {};

  Future<List<Device>> getData() async {
    final snapshot = await _database.child('rfid').once();
    final devicesMap = snapshot.snapshot.value as Map?;
    final devicesList =
        devicesMap?.entries.map((entry) => Device.fromJson(entry)).toList();
    return devicesList ?? [];
  }

  Future getOnlinePermissions() async {
    final snapshot = await _database.child('cards').once();
    final devicesMap = snapshot.snapshot.value as Map?;
    return devicesMap ?? {};
  }

  void listenToChange() {
    _database.child('rfid').onValue.listen((event) async {
      await getIt<AppCubit>().refresh();
      getIt<AppCubit>().checkPermissions();
      getIt<AppCubit>().checkCapacity();
    });
    _database.child('users').onValue.listen((event) async {
      getIt<AppCubit>().refresh();
      String uid = getIt<FirebaseAuthRepo>().currentUser?.uid ?? '';
      currentMail =  event.snapshot.child(uid).child('email').value.toString();
    });
    _database
        .child('users')
        .child(getIt<FirebaseAuthRepo>().currentUser!.uid)
        .child('notifications')
        .onValue
        .listen((event) async {
      getIt<AppCubit>().refresh();
      Map notifications = event.snapshot.value as Map? ?? {};
      if (notifications.isNotEmpty) {
        showToast('Message From Admin', notifications.values.last);
      }
    });
    _database.child('zone_messaging').onValue.listen((event) async {
      zonedMessages = await getIt<FirebaseRealTimeDB>().getMessages();
      await getIt<AppCubit>().refresh();
    });
  }

  Future<void> updateData(Device device) async {
    await _database.child('rfid').child(device.id).update(device.toJson());
  }

  Future<void> deleteData(String id) async {
    await _database.child('rfid').child(id).remove();
  }

  addUser(String name, String email, String zone, String pass) {
    // get user id
    String uid = getIt<FirebaseAuthRepo>().currentUser?.uid ?? '';

    _database.child('users').child(uid).update({
      'name': name,
      'email': email,
      'zone': zone,
      'pass': pass,
      'available': false
    });
  }

  isAdmin()  {
    // String uid = getIt<FirebaseAuthRepo>().currentUser?.uid ?? '';
    // final mail = await _database.child('users').child(uid).child('email').get();
    // String mailValue = mail.value.toString();
    String mailValue = currentMail;
    String adminEmail = "test@gmail.com";
    return adminEmail == mailValue;
  }

  getAdminEmail() async {
    final snapshot = await _database.child('users').once();
    String uid = getIt<FirebaseAuthRepo>().currentUser?.uid ?? '';
    currentMail =  snapshot.snapshot.child(uid).child('email').value.toString();
  }

  getAllUsers() async {
    final snapshot = await _database.child('users').once();
    final usersMap = snapshot.snapshot.value as Map?;
    return usersMap ?? {};
  }

  Future<Map> getMessages() async {
    final snapshot = await _database.child('zone_messaging').once();
    final usersMap = snapshot.snapshot.value as Map?;
    return usersMap ?? {};
  }

  updateZone(String id, String zone) async {
    await _database.child('users').child(id).update({'zone': zone});
  }

  updateAvailable(String id, bool val) async {
    await _database.child('users').child(id).update({'available': val});
  }

  addNotification(String id, String message) async {
    DateTime now = DateTime.now();
    String formattedDate = DateFormat('yyyy-MM-dd HH:mm:ss').format(now);

    await _database.child('users').child(id).child("notifications").update({
      formattedDate: message,
    });
  }

  addMessage(String message, String zone) async {
    DateTime now = DateTime.now();
    String formattedDate = DateFormat('yyyy-MM-dd HH:mm:ss').format(now);

    await _database.child('zone_messaging').child(zone.trim()).child(formattedDate).update({
      'content': message,
      'time': formattedDate,
      'sender_id': getIt<FirebaseAuthRepo>().currentUser?.uid,
      'sender_name': getIt<FirebaseAuthRepo>().currentUser?.displayName
    });
  }

  deleteAllNotifications() async {
    String id = getIt<FirebaseAuthRepo>().currentUser?.uid ?? '';
    await _database.child('zone_messaging').remove();
  }

}

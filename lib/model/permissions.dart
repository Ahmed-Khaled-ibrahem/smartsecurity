import 'package:hive/hive.dart';

class PermissionsRepo {
  List<CardPermission> allCardsPermissions = [];
  var hiveBox = Hive.box('Box');

  PermissionsRepo() {
    readLocalPermissions();
    print('initialized');
  }

  Map<String, dynamic> toMap(List<CardPermission> data) {
    List cards = data.map((card) => card.toMap()).toList();
    return {
      'allCardsPermissions': cards,
    };
  }

  setAllCardsPermissionsFromMap(Map map) {
    List cardsMap = map['allCardsPermissions'] ?? [];
    allCardsPermissions = cardsMap.map((card) => CardPermission.fromMap(card)).toList().cast<CardPermission>();
  }

  setAllCardsPermissions(List<CardPermission> allCardsPermissions) {
    this.allCardsPermissions = allCardsPermissions;
  }

  getAllCardsPermissions() {
    return allCardsPermissions;
  }

  readLocalPermissions() {
    setAllCardsPermissionsFromMap(hiveBox.get('permissions') ?? {});
  }

  saveLocalPermissions(List<CardPermission> data) {
    hiveBox.put('permissions', toMap(data));
  }

  addOnlinePermissions(Map? onlinePermissions) {
    // {'card id':'card name'}
    if (onlinePermissions != null) {
      onlinePermissions.forEach((cardId, cardName) {
        List ids = allCardsPermissions.map((element) => element.cardId).toList();

        if (!ids.contains(cardId)) {
          allCardsPermissions.add(CardPermission(
              cardName: cardName,
              cardId: cardId,
              permissions: Permissions(permissions: [])));
        }
      });
    }
  }
}

class CardPermission {
  String cardName;
  String cardId;
  Permissions permissions;

  CardPermission(
      {required this.cardName,
      required this.cardId,
      required this.permissions});

  toMap() {
    return {
      'cardName': cardName,
      'cardId': cardId,
      'permissions': permissions.toMap(),
    };
  }

  static fromMap(Map map) {
    return CardPermission(
        cardName: map['cardName'],
        cardId: map['cardId'],
        permissions: Permissions.fromMap(map['permissions']));
  }
}

class Permission {
  String espId;
  String espName;
  bool isAllowed;

  Permission(
      {required this.espId, required this.isAllowed, required this.espName});

  toMap() {
    return {
      'espId': espId,
      'espName': espName,
      'isAllowed': isAllowed,
    };
  }

  setEspName(String name) {
    espName = name;
  }

  setEspId(String id) {
    espId = id;
  }

  setIsAllowed(bool isAllowed) {
    this.isAllowed = isAllowed;
  }

  static fromMap(element) {
    return Permission(
        espId: element['espId'],
        espName: element['espName'],
        isAllowed: element['isAllowed']);
  }
}

class Permissions {
  List<Permission> permissions;

  Permissions({required this.permissions});

  toMap() {
    return {
      'permissions': permissions.map((element) => element.toMap()).toList(),
    };
  }

  static fromMap(map) {
    return Permissions(
        permissions: map['permissions']
            .map((element) => Permission.fromMap(element))
            .toList()
            .cast<Permission>());
  }
}

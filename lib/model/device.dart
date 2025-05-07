import 'card.dart';

class Device {
  final String id;
  final String name;
  final String type;
  final int capacity;
  List<RFCard>? cards;

  Device(
      {required this.id,
      required this.name,
      required this.capacity,
      required this.type,
      this.cards});

  factory Device.fromJson(MapEntry<dynamic, dynamic> deviceMap) {
    Map<dynamic, dynamic> json = deviceMap.value;
    return Device(
      id: deviceMap.key,
      name: json['name'] ?? 'unknown',
      type: json['type']?? 'unknown',
      capacity: json['capacity'] ?? 100,
      cards: (json['cards'] as Map?)?.entries.map((entry) => RFCard.fromJson(entry)).toList(),
    );
  }

  get cardCount => cards?.length ?? 0;

  get inside {
    return cards?.where((element) => element.state == "in").length ?? 0;
  }

  Map<String, Object?> toJson() {
    return {
      'id': id,
      'name': name,
      'type': type,
      'capacity': capacity,
    };
  }
}

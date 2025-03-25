class RFCard {
  final String id;
  final String state;

  RFCard(this.id, this.state);

  factory RFCard.fromJson(MapEntry json) {
    return RFCard(json.key, json.value);
  }

  toJson() {
    return {
      'id': id,
      'state': state,
    };
  }

}
class Building {
  final int id;
  final String lgaId;
  final double lat;
  final double lon;
  final bool verified;

  const Building({
    required this.id,
    required this.lgaId,
    required this.lat,
    required this.lon,
    this.verified = false,
  });

  factory Building.fromJson(Map<String, dynamic> json) => Building(
        id: json['id'] as int,
        lgaId: json['lga_id'] as String,
        lat: (json['lat'] as num).toDouble(),
        lon: (json['lon'] as num).toDouble(),
        verified: json['verified'] as bool? ?? false,
      );
}

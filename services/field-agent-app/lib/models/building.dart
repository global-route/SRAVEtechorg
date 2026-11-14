class Building {
  final int id;
  final String lgaId;
  final double lat;
  final double lon;
  final String propertyType;
  final bool verified;
  final String? ownerPhone;
  final String? ownerLanguage;
  final String? photoPath;
  final int synced; // 0=pending, 1=synced, 2=conflict

  const Building({
    required this.id,
    required this.lgaId,
    required this.lat,
    required this.lon,
    required this.propertyType,
    this.verified = false,
    this.ownerPhone,
    this.ownerLanguage,
    this.photoPath,
    this.synced = 0,
  });

  factory Building.fromJson(Map<String, dynamic> j) => Building(
        id: j['id'] as int,
        lgaId: j['lga_id'] as String,
        lat: (j['lat'] as num?)?.toDouble() ?? 0.0,
        lon: (j['lon'] as num?)?.toDouble() ?? 0.0,
        propertyType: j['property_type'] as String? ?? 'residential_low',
        verified: j['verified'] as bool? ?? false,
      );

  factory Building.fromMap(Map<String, dynamic> m) => Building(
        id: m['id'] as int,
        lgaId: m['lga_id'] as String,
        lat: m['lat'] as double,
        lon: m['lon'] as double,
        propertyType: m['property_type'] as String? ?? 'residential_low',
        verified: (m['verified'] as int) == 1,
        ownerPhone: m['owner_phone'] as String?,
        ownerLanguage: m['owner_language'] as String?,
        photoPath: m['photo_path'] as String?,
        synced: m['synced'] as int? ?? 0,
      );

  Map<String, dynamic> toMap() => {
        'id': id,
        'lga_id': lgaId,
        'lat': lat,
        'lon': lon,
        'property_type': propertyType,
        'verified': verified ? 1 : 0,
        'owner_phone': ownerPhone,
        'owner_language': ownerLanguage,
        'photo_path': photoPath,
        'synced': synced,
      };
}

// Run: dart run scripts/cache_tiles.dart --lga NGA025012 --bbox "3.3792,6.5244,3.4000,6.5500" --zoom-min 12 --zoom-max 18
import 'dart:io';

void main(List<String> args) async {
  final params = _parseArgs(args);
  final lga = params['lga'] ?? 'unknown';
  final bbox = (params['bbox'] ?? '').split(',').map(double.parse).toList();
  final zoomMin = int.parse(params['zoom-min'] ?? '12');
  final zoomMax = int.parse(params['zoom-max'] ?? '18');

  if (bbox.length != 4) {
    stderr.writeln('Error: --bbox must be "min_lon,min_lat,max_lon,max_lat"');
    exit(1);
  }

  print('Pre-caching tiles for LGA: $lga');
  print('Bounding box: $bbox');
  print('Zoom levels: $zoomMin–$zoomMax');

  int total = 0;
  for (int z = zoomMin; z <= zoomMax; z++) {
    final count = _tileCount(bbox[0], bbox[1], bbox[2], bbox[3], z);
    total += count;
    print('  Zoom $z: $count tiles');
  }

  print('\nTotal tiles to cache: $total');
  print('Estimated size: ~${(total * 15 / 1024).toStringAsFixed(1)} MB');
  print('\nTODO: integrate Mapbox Offline Regions API to download tiles.');
  print('Run this script on a connected device before field deployment.');
}

int _tileCount(double minLon, double minLat, double maxLon, double maxLat, int zoom) {
  int lon2tile(double lon) => ((lon + 180) / 360 * (1 << zoom)).floor();
  int lat2tile(double lat) {
    final rad = lat * 3.141592653589793 / 180;
    return ((1 - (0.5 / 3.141592653589793) * (rad - (rad * rad * rad / 3))) * (1 << zoom) / 2).floor();
  }
  final xMin = lon2tile(minLon), xMax = lon2tile(maxLon);
  final yMin = lat2tile(maxLat), yMax = lat2tile(minLat);
  return (xMax - xMin + 1) * (yMax - yMin + 1);
}

Map<String, String> _parseArgs(List<String> args) {
  final map = <String, String>{};
  for (int i = 0; i < args.length - 1; i++) {
    if (args[i].startsWith('--')) map[args[i].substring(2)] = args[i + 1];
  }
  return map;
}

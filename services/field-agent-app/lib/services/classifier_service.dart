import 'dart:io';
import 'package:tflite_flutter/tflite_flutter.dart';
import 'package:image/image.dart' as img;

const _labels = ['residential_low', 'residential_high', 'commercial', 'industrial'];

class ClassifierService {
  Interpreter? _interpreter;

  Future<void> load() async {
    _interpreter = await Interpreter.fromAsset('assets/models/yolov8n_cls.tflite');
  }

  Future<({String label, double confidence})> classify(File photo) async {
    if (_interpreter == null) await load();

    final raw = img.decodeImage(await photo.readAsBytes())!;
    final resized = img.copyResize(raw, width: 224, height: 224);

    // Normalise to [0,1] float32
    final input = List.generate(
      1,
      (_) => List.generate(
        224,
        (y) => List.generate(224, (x) {
          final pixel = resized.getPixel(x, y);
          return [pixel.r / 255.0, pixel.g / 255.0, pixel.b / 255.0];
        }),
      ),
    );

    final output = List.filled(4, 0.0).reshape([1, 4]);
    _interpreter!.run(input, output);

    final scores = output[0] as List<double>;
    final maxIdx = scores.indexOf(scores.reduce((a, b) => a > b ? a : b));
    return (label: _labels[maxIdx], confidence: scores[maxIdx]);
  }
}

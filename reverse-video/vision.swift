// On-device text and face detection (Apple Vision) for reverse.py.
//   vision <image> [<image> ...]  ->  JSON array on stdout
// Boxes are [x, y, w, h], 0..1, origin top-left.
import AppKit
import Foundation
import Vision

struct Txt: Codable { var s: String; var c: Double; var b: [Double] }
struct Out: Codable { var file: String; var texts: [Txt]; var faces: [[Double]] }

func box(_ r: CGRect) -> [Double] {
    [Double(r.minX), Double(1 - r.maxY), Double(r.width), Double(r.height)]
}

var results: [Out] = []
for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let text = VNRecognizeTextRequest()
    text.recognitionLevel = .accurate
    text.usesLanguageCorrection = true
    let face = VNDetectFaceRectanglesRequest()
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([text, face])
    var ts: [Txt] = []
    for o in text.results ?? [] {
        if let top = o.topCandidates(1).first {
            ts.append(Txt(s: top.string, c: Double(top.confidence), b: box(o.boundingBox)))
        }
    }
    let fs = (face.results ?? []).map { box($0.boundingBox) }
    results.append(Out(file: path, texts: ts, faces: fs))
}
FileHandle.standardOutput.write(try! JSONEncoder().encode(results))

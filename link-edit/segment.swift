// Person segmentation with Apple's Vision framework (on-device, no model download).
//
//   tools/bin/segment <in_dir> <out_dir> [accurate|balanced|fast]
//       Reads every .png in <in_dir> (sorted) and writes a same-size 8-bit grayscale mask
//       (white = person) with the same file name into <out_dir>.
//   tools/bin/segment --stream <w> <h> [accurate|balanced|fast]
//       Reads raw rgb24 frames of w x h from stdin; for each frame writes a header (mask width, mask
//       height as little-endian uint32) and the mask bytes (8-bit, unpadded) to stdout. Uses a sequence
//       handler so masks stay steady from frame to frame. render.py uses this to put text behind people.
//
// Build: swiftc -O tools/segment.swift -o tools/bin/segment
import AppKit
import CoreImage
import Foundation
import Vision

let args = CommandLine.arguments
func usage() -> Never {
    FileHandle.standardError.write("usage: segment <in_dir> <out_dir> [quality] | segment --stream <w> <h> [quality]\n".data(using: .utf8)!)
    exit(2)
}
guard args.count >= 3 else { usage() }

func qualityLevel(_ s: String?) -> VNGeneratePersonSegmentationRequest.QualityLevel {
    switch s ?? "accurate" {
    case "fast": return .fast
    case "balanced": return .balanced
    default: return .accurate
    }
}

if args[1] == "--stream" {
    guard args.count >= 4, let w = Int(args[2]), let h = Int(args[3]) else { usage() }
    let request = VNGeneratePersonSegmentationRequest()
    request.qualityLevel = qualityLevel(args.count > 4 ? args[4] : nil)
    request.outputPixelFormat = kCVPixelFormatType_OneComponent8
    let seq = VNSequenceRequestHandler()
    let frameBytes = w * h * 3
    let input = FileHandle.standardInput
    let output = FileHandle.standardOutput
    let rgb = CGColorSpaceCreateDeviceRGB()
    while true {
        var data = Data(capacity: frameBytes)
        while data.count < frameBytes {
            let chunk = input.readData(ofLength: frameBytes - data.count)
            if chunk.isEmpty { exit(0) }
            data.append(chunk)
        }
        guard let provider = CGDataProvider(data: data as CFData),
              let cg = CGImage(width: w, height: h, bitsPerComponent: 8, bitsPerPixel: 24, bytesPerRow: w * 3,
                               space: rgb, bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue),
                               provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent)
        else { exit(3) }
        var mw = 0, mh = 0
        var bytes = Data()
        if (try? seq.perform([request], on: cg)) != nil, let buf = request.results?.first?.pixelBuffer {
            CVPixelBufferLockBaseAddress(buf, .readOnly)
            mw = CVPixelBufferGetWidth(buf)
            mh = CVPixelBufferGetHeight(buf)
            let stride = CVPixelBufferGetBytesPerRow(buf)
            let base = CVPixelBufferGetBaseAddress(buf)!.assumingMemoryBound(to: UInt8.self)
            bytes.reserveCapacity(mw * mh)
            for row in 0..<mh { bytes.append(base + row * stride, count: mw) }
            CVPixelBufferUnlockBaseAddress(buf, .readOnly)
        }
        var header = Data()
        for v in [UInt32(mw), UInt32(mh)] { withUnsafeBytes(of: v.littleEndian) { header.append(contentsOf: $0) } }
        output.write(header)
        output.write(bytes)
    }
}

let inDir = URL(fileURLWithPath: args[1])
let outDir = URL(fileURLWithPath: args[2])
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
let files = (try FileManager.default.contentsOfDirectory(at: inDir, includingPropertiesForKeys: nil))
    .filter { $0.pathExtension.lowercased() == "png" }
    .sorted { $0.lastPathComponent < $1.lastPathComponent }
let ctx = CIContext()
let request = VNGeneratePersonSegmentationRequest()
request.qualityLevel = qualityLevel(args.count > 3 ? args[3] : nil)
request.outputPixelFormat = kCVPixelFormatType_OneComponent8

for f in files {
    guard let src = CIImage(contentsOf: f) else { continue }
    let handler = VNImageRequestHandler(ciImage: src, options: [:])
    try handler.perform([request])
    guard let buf = request.results?.first?.pixelBuffer else { continue }
    var mask = CIImage(cvPixelBuffer: buf)
    // the mask comes back smaller than the frame: scale it up to match
    let sx = src.extent.width / mask.extent.width, sy = src.extent.height / mask.extent.height
    mask = mask.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
    guard let cg = ctx.createCGImage(mask, from: src.extent,
                                     format: .L8, colorSpace: CGColorSpaceCreateDeviceGray()) else { continue }
    let rep = NSBitmapImageRep(cgImage: cg)
    try rep.representation(using: .png, properties: [:])!.write(to: outDir.appendingPathComponent(f.lastPathComponent))
}
print("segmented \(files.count) frames")

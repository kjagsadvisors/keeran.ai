// takeone-rec: records the Mac's default microphone to a WAV with Apple's AVAudioRecorder.
// Take One's studio builds this once (swiftc) and runs it when you press Record.
//
//   takeone-rec <out.wav>
//   stdout: "ready <mic name>" once recording, then "L <dB>" about 10 times a second (input level)
//   stop:   write "q" + newline to stdin, or send SIGINT / SIGTERM. The file is finalized, then it prints "done".
//
// Why not ffmpeg: ffmpeg's avfoundation input keeps one audio packet at a time and drops it when the next arrives
// first, which leaves 512-sample gaps that sound like the voice cutting in and out. AVAudioRecorder buffers properly.

import AVFoundation
import Foundation

setvbuf(stdout, nil, _IOLBF, 0)

func fail(_ message: String, _ code: Int32 = 1) -> Never {
    FileHandle.standardError.write(("ERR " + message + "\n").data(using: .utf8)!)
    exit(code)
}

let args = CommandLine.arguments
if args.count < 2 { fail("usage: takeone-rec <out.wav>", 2) }
let url = URL(fileURLWithPath: args[1])

// Microphone permission belongs to the app that started us; ask if it hasn't been decided yet.
if AVCaptureDevice.authorizationStatus(for: .audio) == .notDetermined {
    let wait = DispatchSemaphore(value: 0)
    AVCaptureDevice.requestAccess(for: .audio) { _ in wait.signal() }
    wait.wait()
}
if AVCaptureDevice.authorizationStatus(for: .audio) != .authorized {
    fail("microphone access denied")
}

let settings: [String: Any] = [
    AVFormatIDKey: Int(kAudioFormatLinearPCM),
    AVSampleRateKey: 48000.0,
    AVNumberOfChannelsKey: 1,
    AVLinearPCMBitDepthKey: 16,
    AVLinearPCMIsFloatKey: false,
    AVLinearPCMIsBigEndianKey: false,
    AVLinearPCMIsNonInterleaved: false,
]

let recorder: AVAudioRecorder
do {
    recorder = try AVAudioRecorder(url: url, settings: settings)
} catch {
    fail("could not open the recorder: " + error.localizedDescription)
}
recorder.isMeteringEnabled = true
if !recorder.prepareToRecord() || !recorder.record() {
    fail("could not start recording")
}
print("ready " + (AVCaptureDevice.default(for: .audio)?.localizedName ?? "Microphone"))

var stopped = false
let lock = NSLock()
func stop() {
    lock.lock()
    if stopped { lock.unlock(); return }
    stopped = true
    lock.unlock()
    recorder.stop()
    print("done")
    exit(0)
}

// Level meter on its own queue: if stdout is slow, only the meter waits, never the recording.
let meterQueue = DispatchQueue(label: "meter")
let meter = DispatchSource.makeTimerSource(queue: meterQueue)
meter.schedule(deadline: .now() + 0.1, repeating: 0.1)
meter.setEventHandler {
    recorder.updateMeters()
    print(String(format: "L %.1f", recorder.averagePower(forChannel: 0)))
}
meter.resume()

signal(SIGINT, SIG_IGN)
signal(SIGTERM, SIG_IGN)
let sigint = DispatchSource.makeSignalSource(signal: SIGINT, queue: .main)
sigint.setEventHandler { stop() }
sigint.resume()
let sigterm = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
sigterm.setEventHandler { stop() }
sigterm.resume()

// "q" on stdin stops; so does stdin closing.
Thread.detachNewThread {
    while let line = readLine() {
        if line.contains("q") { break }
    }
    DispatchQueue.main.async { stop() }
}

RunLoop.main.run()

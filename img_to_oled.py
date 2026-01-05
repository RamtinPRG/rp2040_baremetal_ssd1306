#!/usr/bin/env python3

import argparse
import os
from PIL import Image, ImageOps, ImageSequence


WIDTH = 128
HEIGHT = 64
PAGES = HEIGHT // 8
FRAMEBUFFER_SIZE = WIDTH * PAGES


def fit_to_aspect(img, target_aspect, bg_color=(0, 0, 0)):
    w, h = img.size
    img_aspect = w / h

    if img_aspect > target_aspect:
        new_w = w
        new_h = int(w / target_aspect)
    else:
        new_h = h
        new_w = int(h * target_aspect)

    canvas = Image.new("RGB", (new_w, new_h), bg_color)
    canvas.paste(img, ((new_w - w) // 2, (new_h - h) // 2))
    return canvas


def process_frame(img, invert):
    img = img.convert("RGB")
    img = fit_to_aspect(img, target_aspect=2.0)
    img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
    img = img.convert("1", dither=Image.FLOYDSTEINBERG)

    if invert:
        img = ImageOps.invert(img)

    return img


def image_to_framebuffer(img):
    pixels = img.load()
    fb = []

    for page in range(PAGES):
        for x in range(WIDTH):
            byte = 0
            for bit in range(8):
                y = page * 8 + bit
                if pixels[x, y]:
                    byte |= (1 << bit)
            fb.append(byte)

    return fb


def write_c_static(fb, path):
    with open(path, "w") as f:
        f.write("#include <stdint.h>\n\n")
        f.write(f"const uint8_t framebuffer[{FRAMEBUFFER_SIZE}] = {{\n")
        for i in range(0, len(fb), 16):
            f.write(
                "    " + ", ".join(f"0x{b:02X}" for b in fb[i:i+16]) + ",\n")
        f.write("};\n")


def write_c_animated(frames, durations, path):
    with open(path, "w") as f:
        f.write("#include <stdint.h>\n\n")
        f.write(f"#define N_FRAMES {len(frames)}\n\n")

        f.write("const uint16_t frame_durations[N_FRAMES] = {\n    ")
        f.write(", ".join(str(d) for d in durations))
        f.write("\n};\n\n")

        f.write("const uint8_t framebuffer[N_FRAMES][1024] = {\n")
        for fb in frames:
            f.write("    {\n")
            for i in range(0, len(fb), 16):
                f.write("        " +
                        ", ".join(f"0x{b:02X}" for b in fb[i:i+16]) + ",\n")
            f.write("    },\n")
        f.write("};\n")


def write_asm_static(fb, path):
    with open(path, "w") as f:
        for i in range(0, len(fb), 16):
            f.write("    .byte " +
                    ", ".join(f"0x{b:02X}" for b in fb[i:i+16]) + "\n")


def write_asm_animated(frames, durations, path):
    with open(path, "w") as f:
        f.write(f"n_frames: .hword {len(frames)}\n\n")
        f.write("frame_durations:\n")
        f.write("    .hword " + ", ".join(str(d) for d in durations) + "\n")

        for idx, fb in enumerate(frames):
            f.write(f"\nframe_{idx}:\n")
            f.write("    .byte 0x40                       // Data control byte\n")
            for i in range(0, len(fb), 16):
                f.write("    .byte " +
                        ", ".join(f"0x{b:02X}" for b in fb[i:i+16]) + "\n")


def write_durations_txt(durations, out_dir):
    with open(os.path.join(out_dir, "durations.txt"), "w") as f:
        for i, d in enumerate(durations):
            f.write(f"frame_{i:03d}: {d}\n")


def get_frame_duration(frame, default=100):
    return frame.info.get("duration", default)


def main():
    parser = argparse.ArgumentParser(
        description="Convert image or animation to 128x64 OLED image and/or framebuffer"
    )

    parser.add_argument("input", help="Input image / animation")
    parser.add_argument("-o", "--output", help="Output base name or directory")
    parser.add_argument("-i", "--invert", action="store_true",
                        help="Invert image before dithering")
    parser.add_argument("-a", "--animated", action="store_true",
                        help="Treat input as animated")

    parser.add_argument("--image", action="store_true",
                        help="Save processed image(s)")
    parser.add_argument("--buffer", action="store_true",
                        help="Generate framebuffer")
    parser.add_argument("-f", "--format", choices=["c", "asm"],
                        help="Framebuffer format (required if --buffer)")

    args = parser.parse_args()

    if not args.image and not args.buffer:
        parser.error("Specify at least one of --image or --buffer")

    if args.buffer and not args.format:
        parser.error("--format is required when using --buffer")

    base = args.output or os.path.splitext(os.path.basename(args.input))[0]
    img = Image.open(args.input)

    # ---- Animated path ----
    if args.animated:
        frames_img = []
        frames_fb = []
        durations = []

        for frame in ImageSequence.Iterator(img):
            duration = get_frame_duration(frame)
            processed = process_frame(frame, args.invert)

            frames_img.append(processed)
            durations.append(duration)

            if args.buffer:
                frames_fb.append(image_to_framebuffer(processed))

        # Image output
        if args.image:
            out_dir = args.output if args.output else f"{base}_frames"
            os.makedirs(out_dir, exist_ok=True)

            for i, frame in enumerate(frames_img):
                frame.save(os.path.join(out_dir, f"frame_{i:03d}.png"))

            write_durations_txt(durations, out_dir)

        # Buffer output
        if args.buffer:
            if args.format == "c":
                write_c_animated(frames_fb, durations, f"{base}_fb.c")
            else:
                write_asm_animated(frames_fb, durations, f"{base}_fb.S")

    # ---- Static path ----
    else:
        processed = process_frame(img, args.invert)

        if args.image:
            processed.save(f"{base}_128x64.png")

        if args.buffer:
            fb = image_to_framebuffer(processed)
            if args.format == "c":
                write_c_static(fb, f"{base}_fb.c")
            else:
                write_asm_static(fb, f"{base}_fb.S")


if __name__ == "__main__":
    main()

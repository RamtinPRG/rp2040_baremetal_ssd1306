#!/usr/bin/env python3

import argparse
import os
from PIL import Image, ImageOps


WIDTH = 128
HEIGHT = 64
PAGES = HEIGHT // 8


def fit_to_aspect(img, target_aspect, bg_color=(0, 0, 0)):
    w, h = img.size
    img_aspect = w / h

    if img_aspect > target_aspect:
        new_w = w
        new_h = int(w / target_aspect)
    else:
        new_h = h
        new_w = int(h * target_aspect)

    canvas = Image.new("RGBA", (new_w, new_h), bg_color)
    canvas.paste(img, ((new_w - w) // 2, (new_h - h) // 2))
    return canvas


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


def write_c_array(fb, path):
    with open(path, "w") as f:
        f.write("#include <stdint.h>\n\n")
        f.write(f"const uint8_t framebuffer[{len(fb)}] = {{\n")
        for i in range(0, len(fb), 16):
            line = ", ".join(f"0x{b:02X}" for b in fb[i:i+16])
            f.write(f"    {line},\n")
        f.write("};\n")


def write_asm_array(fb, path):
    with open(path, "w") as f:
        for i in range(0, len(fb), 16):
            line = ", ".join(f"0x{b:02X}" for b in fb[i:i+16])
            f.write(f"    .byte {line}\n")


def process_image(input_path, invert):
    img = Image.open(input_path).convert("RGB")
    if invert:
        img = ImageOps.invert(img)
    img = fit_to_aspect(img, target_aspect=2.0)
    img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
    img = img.convert("1", dither=Image.FLOYDSTEINBERG)

    return img


def main():
    parser = argparse.ArgumentParser(
        description="Convert image to 128x64 OLED image and/or framebuffer"
    )

    parser.add_argument("input", help="Input image file")
    parser.add_argument("-o", "--output", help="Base output name (optional)")
    parser.add_argument("-i", "--invert", action="store_true",
                        help="Invert image before dithering")

    parser.add_argument("--image", action="store_true",
                        help="Save processed image")
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
    img = process_image(args.input, args.invert)
    img.show()

    # Save image
    if args.image:
        img_path = None
        if args.output:
            img_path = args.output
        else:
            img_path = f"{base}_128x64.png"
        img.save(img_path)
        print(f"Image saved: {img_path}")

    # Save framebuffer
    if args.buffer:
        fb = image_to_framebuffer(img)
        fb_path = None
        if args.output:
            fb_path = args.output
        else:
            if args.format == "c":
                fb_path = f"{base}_fb.c"
            else:
                fb_path = f"{base}_fb.S"

        if args.format == "c":
            write_c_array(fb, fb_path)
        else:
            write_asm_array(fb, fb_path)
        print(f"Framebuffer saved: {fb_path}")


if __name__ == "__main__":
    main()

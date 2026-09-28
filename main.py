import asyncio
from bleak import BleakClient
from PIL import Image, ImageDraw, ImageFont
import unicodedata
import pandas as pd
# ============================================================
# D11S
# ============================================================

ADDRESS = "C9:48:8A:D1:81:22"

# BLE characteristic ghi dữ liệu
WRITE_UUID = "00002af1-0000-1000-8000-00805f9b34fb"

# BLE characteristic nhận phản hồi
NOTIFY_UUID = "00002af0-0000-1000-8000-00805f9b34fb"

# D11S print head
WIDTH = 96
BYTES_PER_ROW = 12

# 203 DPI ≈ 8 dots/mm
# Tem 40 mm
LABEL_HEIGHT = 50 * 8

# BLE packet
CHUNK_SIZE = 200

# Timing theo implementation đã reverse-engineer
DELAY_COMMAND = 0.05
DELAY_CHUNK = 0.02
DELAY_AFTER_RASTER = 1.0
DELAY_AFTER_FEED = 0.30


# ============================================================
# BLE SEND
# ============================================================

async def send(client, data, name=""):
    print(f"TX {name}: {data.hex(' ')}")

    await client.write_gatt_char(
        WRITE_UUID,
        data,
        response=False
    )

    await asyncio.sleep(DELAY_COMMAND)


async def send_chunked(client, data):

    print(f"Sending {len(data)} bytes...")

    for i in range(0, len(data), CHUNK_SIZE):

        chunk = data[i:i + CHUNK_SIZE]

        await client.write_gatt_char(
            WRITE_UUID,
            chunk,
            response=False
        )

        await asyncio.sleep(DELAY_CHUNK)


# ============================================================
# CREATE TEST LABEL
# ============================================================
def create_test_label(name):
    name_text = unicodedata.normalize('NFC',name)
    # Tem ngang:
    # chiều in theo đầu in = 96 dots
    # chiều dài tem = 320 dots
    #
    # Nội dung sẽ được xoay 90 độ.

    img = Image.new(
        "1",
        (WIDTH, LABEL_HEIGHT),
        1
    )

    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(
            "Agbalumo-Regular.ttf",
            24
        )
    except:
        font = ImageFont.load_default()

    # text1 = "TEST D11S"
    # text2 = "12345"

    # Tạo vùng trung gian để viết chữ
    temp = Image.new(
        "1",
        (LABEL_HEIGHT, WIDTH),
        1
    )

    temp_draw = ImageDraw.Draw(temp)

    bbox1 = temp_draw.textbbox(
        (0, 0),
        name_text,
        font=font
    )

    # bbox2 = temp_draw.textbbox(
    #     (0, 0),
    #     text2,
    #     font=font
    # )

    w1 = bbox1[2] - bbox1[0]
    # w2 = bbox2[2] - bbox2[0]

    temp_draw.text(
        (
            (LABEL_HEIGHT - w1) // 2,
            25
        ),
        name_text,
        font=font,
        fill=0
    )

    # temp_draw.text(
    #     (
    #         (LABEL_HEIGHT - w2) // 2,
    #         55
    #     ),
    #     text2,
    #     font=font,
    #     fill=0
    # )

    # Xoay 90 độ
    temp = temp.rotate(
        90,
        expand=True
    )

    # Cắt/đặt vào vùng 96 x 320
    img.paste(
        temp,
        (
            0,
            0
        )
    )

    return img
# ============================================================
# IMAGE -> D11S RASTER
# ============================================================

def image_to_raster(img):

    # PIL 1-bit image
    #
    # D11S:
    # 1 = black
    # 0 = white
    #
    # PIL mode "1" internally uses:
    # 0 = black
    # 1 = white
    #
    # Therefore invert before packing.

    pixels = img.load()

    raster = bytearray()

    for y in range(img.height):

        for byte_x in range(BYTES_PER_ROW):

            value = 0

            for bit in range(8):

                x = byte_x * 8 + bit

                if x >= WIDTH:
                    continue

                # PIL:
                # 0 = black
                # 1 = white
                #
                # Printer:
                # 1 = black
                # 0 = white

                if pixels[x, y] == 0:

                    value |= (0x80 >> bit)

            raster.append(value)

    return bytes(raster)


# ============================================================
# MAIN PRINT
# ============================================================

# async def main(mylist):

#     print("Connecting to D11S...")

#     async with BleakClient(ADDRESS) as client:

#         print("Connected:", client.is_connected)

#         # ----------------------------------------------------
#         # 1. Set density
#         # ----------------------------------------------------

#         await send(
#             client,
#             bytes([
#                 0x10,
#                 0xFF,
#                 0x10,
#                 0x00,
#                 0x01
#             ]),
#             "density"
#         )

#         # ----------------------------------------------------
#         # 2. Set paper type = GAP
#         #
#         # 00 = gap / label
#         # 01 = black mark
#         # 02 = continuous
#         # ----------------------------------------------------

#         await send(
#             client,
#             bytes([
#                 0x10,
#                 0xFF,
#                 0x84,
#                 0x00
#             ]),
#             "paper GAP"
#         )

#         # ----------------------------------------------------
#         # 3. Wake printer
#         # ----------------------------------------------------

#         await send(
#             client,
#             b"\x00" * 12,
#             "wake"
#         )

#         # ----------------------------------------------------
#         # 4. Enable printer
#         #
#         # AiYin D11S specific
#         # ----------------------------------------------------

#         await send(
#             client,
#             bytes([
#                 0x10,
#                 0xFF,
#                 0xFE,
#                 0x01
#             ]),
#             "enable"
#         )

     
#         for name in mylist:
#             # ----------------------------------------------------
#             # 5. Create image
#             # ----------------------------------------------------
    
#             img = create_test_label(name)
    
#             raster = image_to_raster(img)
    
#             print()
#             print("Label:")
#             print(f"  Width  : {img.width} px")
#             print(f"  Height : {img.height} px")
#             print(f"  Raster : {len(raster)} bytes")
#             print()
    
#             # ----------------------------------------------------
#             # 6. Raster header
#             #
#             # 1D 76 30 00
#             # 0C 00 = 12 bytes wide
#             # yL yH = image height
#             # ----------------------------------------------------
    
#             yl = img.height & 0xFF
#             yh = (img.height >> 8) & 0xFF
    
#             header = bytes([
#                 0x1D,
#                 0x76,
#                 0x30,
#                 0x00,
#                 0x0C,
#                 0x00,
#                 yl,
#                 yh
#             ])
    
#             print(
#                 "Raster header:",
#                 header.hex(" ")
#             )
    
#             # ----------------------------------------------------
#             # 7. Send image
#             # ----------------------------------------------------
    
#             await send_chunked(
#                 client,
#                 header + raster
#             )
    
#             print("Raster sent.")
    
#             # Give print head time
#             await asyncio.sleep(
#                 DELAY_AFTER_RASTER
#             )
#             await asyncio.sleep(5)
#             # ----------------------------------------------------
#             # 8. Move to next label
#             #
#             # D11S detects GAP sensor
#             # ----------------------------------------------------
    
#             await send(
#                 client,
#                 bytes([
#                     0x1D,
#                     0x0C
#                 ]),
#                 "form feed"
#             )
    
#             await asyncio.sleep(
#                 DELAY_AFTER_FEED
#             )

#         # ----------------------------------------------------
#         # 9. Stop print
#         #
#         # AiYin D11S specific
#         # ----------------------------------------------------

#         print("Stopping printer...")

#         await client.write_gatt_char(
#             WRITE_UUID,
#             bytes([
#                 0x10,
#                 0xFF,
#                 0xFE,
#                 0x45
#             ]),
#             response=False
#         )

#         # Printer may take some time to finish
#         await asyncio.sleep(2)

#         print()
#         print("DONE")

async def main(mylist):

    for name in mylist:

        print()
        print("=" * 50)
        print("PRINT:", name)
        print("=" * 50)

        print("Connecting to D11S...")

        async with BleakClient(ADDRESS) as client:

            print("Connected:", client.is_connected)

            # 1. Set density
            await send(
                client,
                bytes([
                    0x10,
                    0xFF,
                    0x10,
                    0x00,
                    0x01
                ]),
                "density"
            )

            # 2. Set paper type = GAP
            await send(
                client,
                bytes([
                    0x10,
                    0xFF,
                    0x84,
                    0x00
                ]),
                "paper GAP"
            )

            # 3. Wake printer
            await send(
                client,
                b"\x00" * 12,
                "wake"
            )

            # 4. Enable printer
            await send(
                client,
                bytes([
                    0x10,
                    0xFF,
                    0xFE,
                    0x01
                ]),
                "enable"
            )

            # 5. Create image
            img = create_test_label(name)

            raster = image_to_raster(img)

            print()
            print("Label:")
            print(f"  Width  : {img.width} px")
            print(f"  Height : {img.height} px")
            print(f"  Raster : {len(raster)} bytes")
            print()

            # 6. Raster header
            yl = img.height & 0xFF
            yh = (img.height >> 8) & 0xFF

            header = bytes([
                0x1D,
                0x76,
                0x30,
                0x00,
                0x0C,
                0x00,
                yl,
                yh
            ])

            print(
                "Raster header:",
                header.hex(" ")
            )

            # 7. Send image
            await send_chunked(
                client,
                header + raster
            )

            print("Raster sent.")

            await asyncio.sleep(
                DELAY_AFTER_RASTER
            )

            # 8. Move to next label
            await send(
                client,
                bytes([
                    0x1D,
                    0x0C
                ]),
                "form feed"
            )

            await asyncio.sleep(
                DELAY_AFTER_FEED
            )

            # 9. Stop print
            print("Stopping printer...")

            await client.write_gatt_char(
                WRITE_UUID,
                bytes([
                    0x10,
                    0xFF,
                    0xFE,
                    0x45
                ]),
                response=False
            )

            await asyncio.sleep(2)

        # BLE connection đã được đóng ở đây
        print("Disconnected.")

        # Nghỉ trước khi reconnect lần kế tiếp
        await asyncio.sleep(1)

    print()
    print("DONE")

# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:
        df = pd.read_excel('list_name.xlsx',header=4)
        ds_column = df.columns.tolist()
        df['HỌ VÀ TÊN'] = df['HỌ VÀ TÊN'].astype(str).str.upper()
        top_6 = (df.iloc[:6]['CHỨC DANH'].fillna('') + ' ' + df.iloc[:6]['HỌ VÀ TÊN']).str.strip().tolist()
        remaining = df.iloc[6:]['HỌ VÀ TÊN'].dropna().tolist()
        list_name = top_6 + remaining
      
        asyncio.run(main(list_name))

    except Exception as e:

        print()
        print("ERROR:")
        print(type(e).__name__)
        print(e)
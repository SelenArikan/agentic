import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from providers.mistral_image import detect_image_suffix, find_tool_file_id


class MistralImageTests(unittest.TestCase):
    def test_find_tool_file_id_from_conversation_response(self):
        response = {
            "outputs": [
                {"type": "tool.execution", "name": "image_generation"},
                {
                    "type": "message.output",
                    "content": [
                        {"type": "text", "text": "Generated the image."},
                        {
                            "type": "tool_file",
                            "tool": "image_generation",
                            "file_id": "file_123",
                            "file_type": "png",
                        },
                    ],
                },
            ]
        }

        self.assertEqual(find_tool_file_id(response), "file_123")

    def test_detect_image_suffix_from_magic_bytes(self):
        self.assertEqual(detect_image_suffix(b"\xff\xd8\xffabc", ".png"), ".jpg")
        self.assertEqual(detect_image_suffix(b"\x89PNG\r\n\x1a\nabc", ".jpg"), ".png")


if __name__ == "__main__":
    unittest.main()

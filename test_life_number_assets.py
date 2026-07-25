import unittest

from life_number_assets import (
    LIFE_NUMBER_IMAGE_BASE_URL,
    life_number_image_share_block,
    life_number_image_url,
)


class LifeNumberAssetsTest(unittest.TestCase):
    def test_each_life_number_maps_to_its_own_image(self):
        for number in range(1, 10):
            with self.subTest(number=number):
                self.assertEqual(
                    life_number_image_url(number),
                    f"{LIFE_NUMBER_IMAGE_BASE_URL}/life-number-{number}.jpg",
                )
                self.assertIn(
                    f"我的 {number} 號人專屬圖卡",
                    life_number_image_share_block(number),
                )

    def test_invalid_life_number_does_not_create_a_link(self):
        for value in (None, "", 0, 10, "unknown"):
            with self.subTest(value=value):
                self.assertEqual(life_number_image_url(value), "")
                self.assertEqual(life_number_image_share_block(value), "")


if __name__ == "__main__":
    unittest.main()

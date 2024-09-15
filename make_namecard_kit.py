import os
from sys import argv

from gkmasToolkit import GkmasManifest
from gkmasToolkit.const import CHARACTER_ABBREVS
from gkmasToolkit.utils import Logger


# general
# - bg_common…
# - frame?
# - misc…
instructions_dl = [
    (r"img_general_icon_contest-rank.*", "profile", None),
    (r"img_general_meishi_illust_idol.*", "idol/full", None),
    (r"img_general_meishi_illust_sd.*", "idol/mini", "2:3"),
    (r"img_general_cidol.*full\..*", "idol/produce", "9:16"),
    (r"img_general_cidol.*thumb-landscape-large.*", "idol/produce", "16:9"),
    (r"img_general_cidol.*thumb-portrait.*", "idol/produce", "3:4"),
    (r"img_general_meishi_illust_sign.*", "idol/sign", None),
    (r"img_general_csprt.*full\..*", "support", "16:9"),
    (r"img_general_meishi_base_story-bg.*", "base/commu", "16:9"),
    (r"img_general_meishi_base_(?!story-bg).*full\..*", "base/misc", "16:9"),
    (r"img_general_achievement_produce.*", "achievement/produce", None),
    (r"img_general_achievement_common.*", "achievement/misc", None),
    (r"img_general_meishi_illust_music-logo.*", "parts/logo", "3:2"),
    (r"img_general_meishi_illust_pict-icon.*", "parts/icon", None),
    (r"img_general_meishi_illust_stamp.*", "parts/misc", None),
    (r"img_general_meishi_illust_hatsuboshi-logo.*", "parts/misc", None),
    (r"img_general_meishi_illust_event.*", "parts/event", None),  # Inferred
    (r"img_general_meishi_illust_highscore.*full\..*", "parts/highscore", None),  # Inferred
    (r"img_general_skillcard.*", "produce/skillcard", None),
    (r"img_general_pitem.*", "produce/pitem", None),
    (r"img_general_pdrink.*", "produce/pdrink", None),
]

# Have to hardcode the number 10, otherwise this requires empty folder post-detection
for char in CHARACTER_ABBREVS[:10]:
    instructions_dl.append(
        (f"img_general_achievement_{char}.*", f"achievement/idol/{char}", None)
    )
    instructions_dl.append(
        (f"img_general_achievement_char_{char}.*", f"achievement/idol/{char}", None)
    )

# These situations are not common enough to be generalized in the module
instructions_pack = [
    ("idol/produce", lambda s: s.split("_")[-2].split("-")[1]),
    ("produce/skillcard", lambda s: s.split("_")[-2]),
]


if __name__ == "__main__":

    assert len(argv) == 2, "Usage: python make_namecard_kit.py <manifest>"
    logger = Logger()

    manifest = GkmasManifest(argv[1])
    target = f"namecard_kit_v{manifest.revision}/"  # output directory

    for pattern, subdir, ratio in instructions_dl:
        logger.info(f"Populating '{subdir}'")
        manifest.download(
            pattern,
            path=target + subdir,
            categorize=False,
            img_resize=ratio,
        )

    for subdir, cat_func in instructions_pack:
        logger.info(f"Post-categorizing '{subdir}'")
        parent = target + subdir
        for f in os.listdir(parent):
            cat = cat_func(f)
            os.makedirs(os.path.join(parent, cat), exist_ok=True)
            os.rename(os.path.join(parent, f), os.path.join(parent, cat, f))
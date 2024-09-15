from gkmasToolkit import GkmasManifest
from sys import argv


# general
# - bg_common…
# - frame?
# - misc…
# achievement
# - idol
# produce
# - skillcard
instructions = [
    ("img_general_icon_contest-rank.*", "profile", None),
    ("img_general_meishi_illust_idol.*", "idol/full", None),
    ("img_general_meishi_illust_sd.*", "idol/mini", "2:3"),
    ("img_general_cidol.*full.*", "idol/produce", "9:16"),
    ("img_general_cidol.*thumb-landscape-large.*", "idol/produce", "16:9"),
    ("img_general_cidol.*thumb-portrait.*", "idol/produce", "3:4"),
    ("img_general_meishi_illust_sign.*", "idol/sign", None),
    ("img_general_csprt.*full.*", "support", "16:9"),
    ("img_general_meishi_base_story-bg.*", "general/bg_commu", "16:9"),
    # ("", "achievement/idol", None),
    ("img_general_achievement_produce.*", "achievement/produce", None),
    ("img_general_achievement_common.*", "achievement/misc", None),
    ("img_general_meishi_illust_music-logo.*", "parts/logo", "3:2"),
    ("img_general_meishi_illust_pict-icon.*", "parts/icon", None),
    ("img_general_meishi_illust_stamp.*", "parts/misc", None),
    ("img_general_meishi_illust_hatsuboshi-logo.*", "parts/misc", None),
    ("img_general_skillcard.*", "produce/skillcard", None),
    ("img_general_pitem.*", "produce/pitem", None),
    ("img_general_pdrink.*", "produce/pdrink", None),
]


if __name__ == "__main__":
    assert len(argv) == 2, "Usage: python make_namecard_kit.py <manifest>"

    manifest = GkmasManifest(argv[1])
    target = f"namecard_kit_v{manifest.revision}/"  # output directory

    for pattern, subdir, ratio in instructions:
        manifest.download(
            pattern,
            path=target + subdir,
            categorize=False,
            img_resize=ratio,
        )

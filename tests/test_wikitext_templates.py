from media2commons.wikitext import (
    commons_filename_from_url,
    find_template,
    set_template_parameters,
)

# A file page as the source wiki writes them.
BILD = """{{Bild
|Genre=Fotografien
|Quellangaben=Stadtarchiv Fürth
|UploadCommons=Nein
|Lizenz=cc-by-sa-3.0
|Beschreibung=Luftbild des "alten" [[Gänsberg]]s
}}"""


def test_a_commons_url_yields_the_plain_file_name():
    url = "https://commons.wikimedia.org/wiki/File:%27Alter%27_G%C3%A4nsberg.jpg"

    assert commons_filename_from_url(url) == "'Alter' Gänsberg.jpg"


def test_a_url_without_a_file_prefix_yields_nothing():
    assert commons_filename_from_url("https://commons.wikimedia.org/wiki/Main") == ""
    assert commons_filename_from_url("") == ""


def test_an_existing_parameter_is_overwritten_in_place():
    updated = set_template_parameters(BILD, {"UploadCommons": "Ja"})

    assert "|UploadCommons=Ja\n" in updated
    assert "Nein" not in updated
    # Everything else survives untouched.
    assert "|Genre=Fotografien\n" in updated
    assert '|Beschreibung=Luftbild des "alten" [[Gänsberg]]s\n' in updated


def test_a_missing_parameter_is_appended_in_the_same_layout():
    updated = set_template_parameters(BILD, {"CommonsLink": "Rathaus.jpg"})

    assert updated.endswith("|CommonsLink=Rathaus.jpg\n}}")


def test_setting_what_is_already_there_changes_nothing():
    once = set_template_parameters(BILD, {"UploadCommons": "Ja"})

    assert set_template_parameters(once, {"UploadCommons": "Ja"}) == once


def test_other_media_types_use_their_own_template():
    audio = "{{Audio\n|Länge=8:01 Minuten\n|UploadCommons=Nein\n}}"

    updated = set_template_parameters(audio, {"UploadCommons": "Ja"})

    assert "|UploadCommons=Ja\n" in updated


def test_a_page_without_a_form_template_is_left_alone():
    assert set_template_parameters("Just some text.", {"UploadCommons": "Ja"}) is None
    assert set_template_parameters("{{Löschantrag}}", {"UploadCommons": "Ja"}) is None


def test_the_form_template_is_found_past_other_templates():
    text = "{{Löschantrag|Grund=unklar}}\n" + BILD

    start, end = find_template(text)

    assert text[start:end] == BILD


def test_pipes_inside_links_and_templates_are_not_parameter_separators():
    text = (
        "{{Bild\n"
        "|Beschreibung=Das [[Rathaus|Fürther Rathaus]] mit {{nowrap|1=a|2=b}}\n"
        "|Lizenz=cc-by-sa-3.0\n"
        "}}"
    )

    updated = set_template_parameters(text, {"UploadCommons": "Ja"})

    assert "[[Rathaus|Fürther Rathaus]] mit {{nowrap|1=a|2=b}}\n" in updated
    assert updated.count("|UploadCommons=Ja") == 1


def test_text_around_the_template_is_preserved():
    text = f"Vorspann\n{BILD}\n[[Kategorie:Bilder]]"

    updated = set_template_parameters(text, {"UploadCommons": "Ja"})

    assert updated.startswith("Vorspann\n")
    assert updated.endswith("\n[[Kategorie:Bilder]]")


def test_both_parameters_can_be_set_at_once():
    updated = set_template_parameters(
        BILD, {"UploadCommons": "Ja", "CommonsLink": "Rathaus.jpg"}
    )

    assert "|UploadCommons=Ja\n" in updated
    assert "|CommonsLink=Rathaus.jpg\n" in updated

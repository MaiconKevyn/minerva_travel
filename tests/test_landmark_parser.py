from minerva_travel.landmark_parser import _parse_response_payload


def test_parse_response_payload_accepts_child_friendly_descriptions():
    response = {
        "output_text": (
            '{"landmarks":[{'
            '"name":"Cristo Redentor",'
            '"city":"Rio de Janeiro",'
            '"country":"Brasil",'
            '"description":["O Cristo Redentor fica no alto do Corcovado.",'
            '"De la, da para imaginar a cidade inteira como um mapa gigante."],'
            '"confidence":0.98'
            "}]}"
        )
    }

    parsed = _parse_response_payload(response)

    assert parsed.landmarks[0].description == [
        "O Cristo Redentor fica no alto do Corcovado.",
        "De la, da para imaginar a cidade inteira como um mapa gigante.",
    ]

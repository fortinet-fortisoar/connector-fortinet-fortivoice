DEVICE_ENDPOINT = "/api/v1/DeviceSip_phone"

GET_NON_ASSIGNED_DEVICES_PAYLOAD = {
                "compoundSearch": [
                    {
                        "searchValues": [
                            {
                                "filter_content": 1
                            }
                        ],
                        "filter_type": 1,
                        "is_negated": False
                    }
                ]
            }
import requests
import time
from elasticsearch import Elasticsearch, helpers, exceptions
from concurrent.futures import ThreadPoolExecutor
import datetime
import json


def batch_check_documents_exist(es, index_names, ids):
    """
    Check existence of multiple documents in given indices.
    Returns a dictionary mapping each id to a boolean value indicating its existence.
    """
    body = []
    for index_name in index_names:
        for doc_id in ids:
            body.append({"index": index_name})
            body.append({"query": {"terms": {"_id": [doc_id]}}})
    
        responses = es.msearch(body=body)
        existence_map = {}
        for i, doc_id in enumerate(ids):
            response = responses["responses"][i * len(index_names)]
            
            # Check if "hits" field exists in the response
            if "hits" in response and "hits" in response["hits"] and response["hits"]["total"]["value"] > 0:
                hits = response["hits"]["hits"]
                existence_map[doc_id] = bool(hits)
            else:
                existence_map[doc_id] = False
        else:
            print(f"Unexpected response format for doc_id: {doc_id}.")
            existence_map[doc_id] = False

    
    existence_map = {}
    for i, doc_id in enumerate(ids):
        hits = responses["responses"][i * len(index_names)]["hits"]["hits"]
        existence_map[doc_id] = bool(hits)
    return existence_map
def get_index_name(base_name, offset_days=0):
    """Return the index name with a specific date appended."""
    date_str = (datetime.datetime.utcnow() - datetime.timedelta(days=offset_days)).strftime('%Y.%m.%d')
    return f"{base_name}_{date_str}"

def document_exists_in_index(es, index_name, document_id):
    """Check if a document with a specific ID exists in the given index."""
    return es.exists(index=index_name, id=document_id)

def flatten_list_fields(data, parent_key=''):
    """
    Recursively flatten dictionary fields that have list values.
    Example:
        data = {"domain_risk": {"components": [{"name": "proximity"}, {"name": "threat_profile"}]}}
        => {"domain_risk.components.name1": "proximity", "domain_risk.components.name2": "threat_profile"}
    """
    items = {}
    for k, v in data.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, list):
            for idx, item in enumerate(v, start=1):
                if idx > 5:  # Only enumerate fields up to 5
                    break
                if isinstance(item, dict):
                    items.update(flatten_list_fields(item, f"{new_key}{idx}"))
                else:
                    items[f"{new_key}{idx}"] = item
        elif isinstance(v, dict):
            items.update(flatten_list_fields(v, new_key))
        else:
            items[new_key] = v
    return items

def main(data, context):
    def iris_investigate_api(initial_hashes):
        api_key = 'dt_api'
        api_username = 'user'
        base_url = 'https://api.domaintools.com/v1/'
        endpoint = 'iris-investigate'

        params = {
            'search_hash': None,
            'app_partner': 'Solutions_Engineering',
            'app_name': 'Hourly_Hot_list',
            'app_version': '1.4',
            'api_username': api_username,
            'api_key': api_key
        }

        results_list = []

        for search_hash in initial_hashes:
            params['search_hash'] = search_hash
            domains_for_hash = 0  # Reset counter for each hash
            results_for_hash = []  # Stores the results for the current hash
            if 'position' in params:  # Reset the position for each hash
                del params['position']

            retry_count = 0
            while retry_count < 3:
                try:
                    has_more_results = True
                    while has_more_results:
                        response = requests.get(f'{base_url}{endpoint}', params=params)

                        if response.status_code == 503:
                            print("Received 503 error. Pausing for 30 seconds...")
                            time.sleep(30)
                            continue  # Retry the request

                        data = response.json()
                        if "limit_exceeded" in data['response'] and data['response']['limit_exceeded'] is True:
                            print(f"Limit exceeded for hash {search_hash}. Results count: {data['response']['message']}")
                            break  # Exit the while loop for the current hash

                        results_for_page = data['response']['results']
                        results_for_hash.extend(results_for_page)
                        domains_for_hash += len(results_for_page)

                        has_more_results = data['response'].get('has_more_results', False)
                        if has_more_results:
                            params['position'] = data['response']['position']

                    results_list.extend(results_for_hash)  # Append the results for this hash to the overall results
                    print(f"Found {domains_for_hash} domains for hash {search_hash}.")
                    break  # Break out of the retry loop if successful

                except requests.exceptions.RequestException as e:
                    print(f'Request error: {e}. Retrying in 30 seconds...')
                    time.sleep(30)
                    retry_count += 1

        return results_list  # Return the overall results after processing all hashes


    def remove_empty_or_none(d):
        """Recursively remove dictionary entries where value is empty or None"""
        if not isinstance(d, (dict, list)):
            return d
        if isinstance(d, list):
            return [v for v in (remove_empty_or_none(v) for v in d) if v]
        return {k: v for k, v in ((k, remove_empty_or_none(v)) for k, v in d.items()) if v}

    
    initial_hashes = [ 'U2FsdGVkX181UzqXoY9jQx90iyvdOXFxVZCKgQ+9/kLQ1q2dXWUytrGSOGXvYjcpiE9FutyRTg0HTqZoW055YuG2Iyec+dHS/lLPXUcxvQ9BC83aXMkXx63qHrJPBI5I1VwyugJCqU3XexlHhon3fypDU3OlHqLhK/QhxyuI1XfBHoHF09vbRQ0ENgY7WG7S2jC/GaOGemdTiQ+qft2TTdhmlq363oSB7b8PZxb88ryd4ByZfjvkTLqkz06tA9RIKOin0062OvQbxy7jbrChVTzP0hZiy+sP/aeM567wGsse3IBRl3QrWCMR2+n+vePR', #90
                'U2FsdGVkX1/8HaCfjMnv7+rwyMJWp2VN6Y4JTyWQCu2a56xqddQsil6puYNZ2LpS/VCXc2COmVnzdbLOjfMbqvimVSO2sEnrH324BXGHmDx1AGUCCUfYO3AOVP4xktCuWU2ATF/K3+lMZg6maDw6+QC0CstJ7/b5za1JbTnKzEcXkhgCAhKRMO/o+Vo4iUdGGhbJrqdamfAvyHWIokTGVXT5TusG2YPtbXoMpsQfuMYM2cmSZSr/FTVS4ZRVAL1/cUJwZAxKpA8X4OgzSrihLTViwLY+MxIdYkL7x1/MoLJ0nhCRIGjGqAnMFeCp2N4x', #91
                'U2FsdGVkX1/djUIxM7Ncp0fbZbjOg/lMAMWQxHeIOQZSL+RXwx5opRa4nQlN9LWGFUKcM1cqJoN3YITwI0hJoYBTE1RHv6T4iXSFWChZzwOLcigc6Yfe5oapVs6qXYBaiPKq6pB0ZiadWRYDg2SDuKFskqnh/5fmoNw1yH9iQ9CA8GFl4NBqg9rZgAAj2ty9oRZM/kCGUAsMLeyPkAt4HjgrYoipNOno8k1ML/dnSRaM/ctCXhx6qZRs/ckealCAeQiF4SppANrDsr51PTC/gMThhDTWe/5EEHRcDs3xc6dNu9aN5DoLHhKW42uoW8s3', #92
                'U2FsdGVkX1/dHLalPvmOyu7Un+NIuZmrB2EvCytuT81XCGRwwPEhIk6Egx3cXoxTglyQ4pcsr5F+BDNg1aE6XePcRNDCJaneQzaD5O4TX/mHYsuaxWXb4bKwUwZVASs1G/j+mTJ3jPYsXdgmtf04dvVIOo80ndm487739g4RIs45j/0ufVQlUm5pZdJfqvetWRfSFF2R2Izq1sboPQwwUBbPM1z/sQgJSXoqbiYkstdXcugKnkL8O41u6bbF05sp25yGkNuU3y37EkKBBdgE9c00fzHDCZs0ihEKbURE4cuV6p459jzZjXzj0PqDWAio', #93
                'U2FsdGVkX1/J+rxXXLYjs4yEprJz/+bgcY4T/VIw7DRAzB2NFMn7LIc85D4vP4toGgwQNyr2QZ95FsHUp86ELgP5tRxB/Z0yPRAHvjYjPn9kzOGc7h4XBLFVcFVlbcAW2syiSa81rBJPYhRZ8dRcMWWxKTLCUCTGiNwUy16Mt39WUeUVXm/ZDAu95/p/+UiA8FPhouKFsAMV16w/x/0APOSRpjwYidOcnj0ISqnKxDGPvKsNNKXrdLUMDYvXBrALfaExXK78VJdoLIFQ+YM74jjrDhsbFxEK3oQNW70O13s58O/JFBaB/+tiQvZKFpYi', #94
                'U2FsdGVkX18SDfISn/6t6WFHBMefUTH4q5qFf5SnmMuwpKF+u3EgeoJ6DrEZghj7pT03wJ4Qh7R3N/tUbtpLUBCIFchMVPjWndRYrrp3FPLEbKnaBcw6G/ARxkB9tInXs94zJHvmFcOIj47yEoJyP+1RlEt24kzW01gi8WMI/DmXg4bMWnEiYthKvacrG+uxhXzjAJLiH8RtWTLd9IOsTi9JpkEwMSM5VXaygKR/0EQb5ZBtO/+7lJK0TyQlYXJ8bIWa4S+MHjsC2v5LaQBQFIU67yUGCmNKlK1XPv71LICZNAAP3733GEEvEagd0OiX', #95
                'U2FsdGVkX1/PrSHdyTFOlSegppBT3h43qnAjPfpnqs+om8FIPW+pNKX+ZxSP/C3v5IGtB5Zw4yBcToBHm5N4pEPwQwIPw1YJv3Q6MTkgH4SoGpwi5kjdoZuiIA+eVTZz1aFkyjLsVWnVlhj7eBn25IM2AcN63H6eOWYRiDQLV9v3Ecg9R2jPh0YhXQj0CnnY8l98f4GzKV4PNf2z5oOQnmBCNNdaPKWOJ/V43jUPIu/GculcFtG+e3xJyfiNhro3oiTt7+EIwE5ZkBdJL/Vj5AYCDU5cVWBQxOm0238oo0swBpG0ujeoQh+iZLP3VPZJ', #96
                'U2FsdGVkX19QIXWU3uQmjMD8Ekxl2WvoLjth8FBJrwK6iAgu2wsgKZW54x6+4L9TUl4oZ2JnA3NA1Miw2E9HRLh41xbzXIpxeZoF1s5WjJJVD9stfZ8O1Ir4tF2A5I+a61VflWX47s+WtGXXUi8qpdPAZdlhb6Hl1M3ive7Mnjw5JERVEy+b0KmRx0DRQc4NIEGiY4aqUlq/Ui33vhkyLkxlgAtQoGJNuy+nnJCDM4+okINeATgUQTwLeFGA9hhgNZD4vTgTu0GeGBuxzX5ProAkLBf3g98+8GxvApB5nVF7EDuvgn0G0P2bLngdHKnu', #97
                'U2FsdGVkX1+nHl7WfTtz9TofliLN+2KwhEKvb2qGUiC772eM0rEZZdGL7lO3PEEwkmZno8iWBjUSNGG8BG8xsSiYKRWTkDUaWrk89miPZUoh879RxQu5TqQEOZVtIAxX+pWYA4PwIv7FUsUV+h50g3Cdgn3XfYqjwFcDEfgPMJAte5HlDygrPu9qlGrY0ppF21nMw7FWoYKRIAijKiXKEn+XqtAZ9y218fZeWMgfJ+gkzUfm7mkoPmZTj7Mbc5BcaeyjvhtX8/SMtl9VKCr/d+K6uhaIFT5PiSj0q62i383EYaNY587IH+QHVSxi1rs9', #98
                'U2FsdGVkX18AWY9gDqvypbaT0hzEVyUzcD9cT5VCZ+5Ft3bZWEXlu+sPLi0S5z6mI/no2pJU6tgA6/IXH3JsWO2snHfGO0dxLqW9SgpCS1NdzXncMvFvoTWK1xsHOsSY/aLzWkohwMl9Izw/PjUlNufpLk3CubosRvCTrvvEqg7Q9qyy+xX5W2/6d8T8tljZtyR2BwfmYIwD6VP4l9G3a3Ic7fcFq4ftui8jhUQxv5gCbw7y+2lyWVxE3fpo7MjSZLPBRpeWJl6QT4OChl9S/50rWt9ogXoT4A7Oj4VPcCJFjtQambFFX0yqbnxJZCpa', #99
                'U2FsdGVkX19Nssq/yXujcfeU4vuGbufSJu5Y5x5wStrEiCXuXiUZt4KMzvTWRqFsOzYw/aI4eV42jZyJ9pEHrhdtSCCBMl1mA7JKLDJ1pN0Fs3Txdl7Abr2/T4Vq7wDA0TBcqD72CTmT7X5uN0y8vTCulVpJTj/E/XIfRLXwiXkKxMSy4lBCPxWX1+nirY6AXb2iAQU2Oo/fWfxuzb2bvSlKumi5H6Q7YCD4fg8H1Q2yeZM31JUAPbsXO9XdDCiuViokLWYo9xD7teQpcNOLTAcFM4LsdYQxBdkQTjnqDUWmSPQiVWGNXQjx4DmAxFhu', #100
                'U2FsdGVkX1/0vpL3dYXCB9iRYaxfSq6aATPOy6f+6IH4nS7TcSNZNSPMu7VOCVEFgenih7/XqZ0DTjVWNEZTOgbglBqkhrOetQNRNq9j+J04YxAwMh88PtJmrE4cKSjqRVk/UFeWKYIW2Kr4jnBS9V4MJJjRIkdY8FS2pkv/+pqjDkIH9iZyAWcAEhPKHEHYaUZmUg0ANgjmBRkKH1T7SglkS6N3l9d0Hz0PUcM0c4xgzcY8gbCMa9sfyc5ueW9d+lvEo3w7rtSiDAyjhcT+Vw==', #70
                'U2FsdGVkX19adrNxs4lcVzvrXNiH6GHiic0jUrlS/Dsfj3eDhx+caeKxt3g/2n5pBrOS7unrjRvMBKHNSMhWFVH9gcGvJfSkVSWGvCIPcaZu5O4Q9CrdKSoDweqoBE9SHbuiZXEME3G0iPs7CykCg30jVJ61El707JtefsWIsEVTXIhIf1UPbBDb71vI4BZiAMHB5X5mEs7+BFapdUqg2mmu3A7hZ/1LSSgvc7kDetw2W3ZDztUJZ1fzJDkAxSyiOaLZVAwG7y3gqo8/vuktUg==', #71
                'U2FsdGVkX1/EpQcXhUNeqbgESN6X6CKYEdlKjhMFO27/iPxspxEI/oBDOOu/s38ygTp1/zOMKe41i7FDjNU771OrkdRwV+2xZQumWYoBfo36eiYgR0MgG4EuvHU2Jnhb7QIahHsdhlUvCJUETy7xcT+8NnUHFbNbZv2h6D8qQig/rs6he4uWahP8lIiEXeTAh8p2r6TqiAxegbPJZOyoD39uQZpDJaToIEv/03JY4UxOoDbM1r7rnm+cnOMJ/5ZSoSmjPx7e+k3sDOFdkZWikg==', #72
                'U2FsdGVkX18kWPpBzztdFI+1fPOpl6lSD/Qv60RwGt356Whefu7U2/EDGjuljq+gWxMrKFeYh7PGSK8GazaWKdnmvlBvihObd1GD2Z3UpjtWrhqryLGWaAMrRYX7ZGg4NNOzkb6c0JC8qADZfyhJK0t5n0KxSdwJmsBAPNTEQJ0Z2Aan35k1QYUu5erWhFDodIoIOeH12TSFnRu935jdzEDMSxazt6KTX7gGAZKH1hbaROJK2OYMzX4IgxtqzSajg2QvTxrVkPewCDxg1F08cg==', #73
                'U2FsdGVkX1+zVhCtYVCH+C0mGIdZUXCltzUkfJ14sQtWWt+YIt9I8CodVEPwL8SRtyEvK8wBioTsjLdy5WK1MsBhr8dMj1C83HTzWzBCdhGhF5s5Ip+/dolJV4JSp7DwZQXHGy3ITWi88k9SDyEHvQU62ed2fiaEpaPa3/uWYh9jWikBhrTF8qt1+Y7y9ZpF+feqGHG4jyuUfVe5ztMGQPyjE1SL8+DaphwELatYSNOLQNJD7O9ngz01yZzD0+xr3ZxCLIm+mjyg56j/DaIRAA==', #74
                'U2FsdGVkX19HTO9mSb5vcQ5VjtYFh2omjGVp2WrV8TcJKbLrtYYcLLbuia7Xy21S7/+7sqsmE4d8XZ4m26ETYSIbcW7DOzeyqnic97lRKMpbY1ovsRNIvgCdAVGPhHyXEq6XPUJkdbH9q2C+98XncLzC2Zu23VFdSBv2uqGdWGC3/ztelTVkwAK5CaRthCzgNq7Uisi5MIhW57dG3loHL/FpNFs+58clUgqvR/nyez2Rni8tcgKemXoKiE8+lZdk824uDm4pTFiY+rok0w1QAg==', #75
                'U2FsdGVkX1/SIFA2WoZALIxJ9weTOXGcSuRoqxy9hNjd5oLU7tWxAlcneQ74pTGtefFa33yDe+CgKeYOd0uF+RxENF0bKUfHBJTg+8tFd3d93iWA7jGzqCQzRsb8ZYUoKhXzC3jGv/Xs6ypOUV94YXNwsgGR28m1VHPyr6X++9tyhn5XMgyK822aJV7gu7ZOX7uzFIlIxsMnElfjj0Zk1SURU2xdoJ6lC8T8Ni8PRLjJE1U+2NCoRDDwvZEdfB60XLfKCfhYCh4DLprAHk80UQ==', #76
                'U2FsdGVkX19SNw6WSzzwXiAh24zVhDH5OXeL33ucfrBT7uw3DncEtO6s+GbaXj3PoJo6SRMRyH8HysCuIgiVeHWyaSHJbPUcvHRP76bkBvii+pAgynCsnTH/ZezlO8DI64LRp1H/mdDkbee+ai8fFM/VWp3uoMYI+ZCuwcPIyHZN3aMzgGgyn5fnIpKnS8GKAUVf8WTJ48Zey/qQjWCia2ZuhdaQKU2iSnaQ9MbD4iZNs7mmcEBX2w/+LyiDRboXWmYJmIifE+wp4TSPGSVV6w==', #77
                'U2FsdGVkX18EzqfnRrFNW5Qpt2NlhWLGRUYGkVRCm+KHiHndSfm+v7176TO2DqPr5VbsLBoxxvfjF/En0lj0KU4ATJ6z+sqUSAi2xox3tK6jFmOWSVxu/8ZlCB4406KZXr4yxcbG5w2qOTvhWSuT/xDaDb1HHO7PeL+k8QZl1a4cxrx1LjJdxq/zZGXB5plA3v1j0u2SwFJBAIXfLQuccX82kyBQbuCP3I67UVLYm1sYNUHWj0rk+Itn8wanTFjt7ofUaOe4Dcc+S7vY7s0oXA==', #78
                'U2FsdGVkX1+f8j8LMUGw9mdiYH+U5+IGytOzFg/vU7R96xhBb4jpOSdvx3y9H+KK15CEABGhoo+qesbsRWq3i6OTo98YCSQyOJbysTofwhf3vk/vipr0GFUZLJSddDlesmZ5V9IVmSuOK0HZOVZL9L56OSCKOOHDH7Vlmmgh5COHnZbCqcwsTy2VbSxaOsOD2R/NPVeIbaqu7loJEUGspAR/JB/JEYDDM+8nFeoqWusp4EAqfYTQ7ZXkRYIXxNnxzJ4C2aWM8L+JncgjywO5cg==', #79
                'U2FsdGVkX18aI+EaLrFxxGcCfXh9astzhUGnRBxwHoNMN/nD7qWVhZpRLtL8RvysKdXr33gjCrsJ+WXoNBwLjvk+S4jl955EEy3VnmYKLJh8WmVE3Vui12HnFq+QqOgUrTGjf+cC8Scbd/eRz43pO0UYC+mXrvQgLHVXiOwjkX2GtkO7S8f0uzKx8IZhWnpXWugFvuoDv2QhYIK5/cTw2boVOiW+H+/bWQs5em1z46xiMRRLDQ74IjKqB9d4Yt3urBUEk5FBpFSxzURWuHSwQw==', #80
                'U2FsdGVkX1+BjcxfChMJce3Yv0R8w6E7/dUAZY1wNfWgHXqMtTvO+WrN1TqUg1shMx9Krqr18teoA6WciKh7cap1AHPd0UXxima3/dFD/K/W+UCrNBi4Mxo1mbp9a9QIVfLUjl/K7Gnl2mGcfqgAOwxcqoOKrVWdqFBJcLPbWd+i15bmtF7JQhr+VTLf46aDn+/mOo57wUs/6U3AsK0emKYiKGAagqhZ2r1Tbpn15bMUMlPtpar/cblTbd5J+9hTWOhg5KQ2vC2PoGkEQut+Jw==', #81
                'U2FsdGVkX1+VJ5QtfNq8gWveo+LsXH+cIfTZ6VFMnUHbTs+GpW736wIlXV9i9nd+PXZJ2q2Ss8Ip8hQCZmECs9yZGqvJkNSZGCKHj2ZD1BlRM+uSmCJtQ2bKBQJ+ATXNdopJmnwvZyIR5eeikMCtEGAvsrcFSKvXTB25FZnpDaz/5vPUszlwHFr+pFQFIW57bGhZmwULR3vRUngCXT2zfwhwdK4S0PVa5HamxUyWkWjc1iV1JLcpj5AKl5oCkl0qpD177bJIfQnkvq1T8/gNCg==', #82
                'U2FsdGVkX19MCT63KlFdcjUht2afT8OxKtF7DT4XBFg9kIx579KX76M4lj2e0rNOGLjSER8JiebmDiF43vnIYMwRAvRPzjw6qBWoeTsv5NLp9SyP4Qh9MbdUsWI63da3Z7XQ5Rbq/DQYDgdm9iYyAQIkIrVybcFbeLpoz1AnQfwOaY5QuSU4H+JMaGvnLMFroCI6q0sO8G/rWftGR36+alM0Dry3J+AJoiq0hFsl7jZq69kWvAghjLvYMuYFzTmS/WGlo6U1ppN571ij8398mw==', #83
                'U2FsdGVkX18XcTvyJpHP8vjCxChqO4qe9rG2VwV7U14QBNc0Qo2JzMJ9zYmRiUJL7xWiCSGjnhnUfX0Ic327e5QukgrE/maKArpRr+MBaK/2T5GGxixjOis/NI1YmKv0dXQFVofLXuLIEq4r0kzkcr7LJ2MbXa11yfhoD7FnfN0aPF1N1PjRlRu3TL/g8Iu4PHUEbXn/vXQ1inZvg062RB/7bQX3NtNSG4TxMBhLl+ch57sgHRIz9lWOL5oNe+xzvXhQqwGAL7BzHJWRGbtmiA==', #84
                'U2FsdGVkX1/vdcEX0A9hkt41lrlPWv3tk6M8C3ZME9YF8+L6WUl1tSaCJCmC577pJ5OefolimW7rOkBAyefm0+L26Aac+CZvr1VTzJ33dofnDMGZ19tbQVfQ7U+bJYI6sDriJXT0XjBRaBAYFaDQYzRVBIXePn6Y+9MP6l8fMkzBfRwG/56sRm9QOPbp5WLx2vYdgm7FJRtDRZej8UfloooZXGrCuUqERFLtitFJBB9HI55tiKuDbR7msNY3U7MLXYdZLEYENpz1IpEZEp3E8A==', #85
                'U2FsdGVkX1/Q34Jfiw7fePhyDSL/TUJ+FNcgxK/AbWEXbp2299cQlClP8rlJpgaKSd5wv7mtgDxe8+bbRlUwTiQGYD6N37AiZT8vFTJQJrZgGUzXqDO7CzIa1W/HU8jw+K/L+PKsut1T+rJmcO1+jP2j8ymOjXqlu60g4orlrmnydgILufJoyBjO0yBU3mhiCUu5HUCTKBDWKdjrQ1G6EcsbiG+sdKmO1MQ0H0w+D2cwUGgZDtP72Zjbg1wx698DDaPahc8QHv+cB5NDqHYL5Q==', #86
                'U2FsdGVkX18TuNnii9qauU+3MQn1r6z0jdNPtpkuDU1wm48w8s0SrHiDXniDe73VM5ZKM4/hkXgEP9MIOANquqd7At7hJcQR3ZnU1sJFVkxyWKb4ylHK6iXIcUirifn7In5thWx5VqFvY9p/jlZLwXUBwxI8/mxrVH74op4fbCsgT2yyxtf+WVYdOVip54rkYWKybb+/SrhIcMFf8CnTM0YSphBF39PlfgZY/vcN+ag9hNwlTnJ5T3IqFUVntd3GdvZ9kTZWG/q+JiMfjqd/EQ==', #87
                'U2FsdGVkX18PYOF7ORNEmBy/ASr+k4AZORebN/0p2vuKLNFVttYg+7FN4TvYJBuMDioFdetgPscoRrBnOHhVUiUS5y6IpnyEFAo4vqg77KupVnVhLyFAhZh3YukGmU2JtRzceH6HPzM4Gqj0xUrK/oDlAIROz3Zon0/IxfJ5MF4OKxaqsZtb6Eu2Ah4Ix2FAXJIDJZuF222OfKbRM7N6xE8EY5Ntnqi0a3yRAjkiTwa+GwYty2WXMznjZRc0zgxfOnE5FSqHKaXeEc7S7nwWIw==', #88
                'U2FsdGVkX1/IE/n1uFEmLbZ0maSiMix7u7+9ZQR4V7ms4WLSlNBGMz2Dbx8TojxuEhorW8EdoOv6ZmPim/bgTttowOJhWa9c8ZY35ozyjuyPbrwm4yHQYmkIULSBpH4rcQWbqy5L1wTbSZOfkwjKhs1UNbkx60yokKDyuJOUtmXqdktlOGhhsv2IHTmELg0JhUTwslPAg6VXj6/wfhDmsuz7WswUbDG5sRo34mEz2464EZ3m2RFDtAdqtEKxRbh5EOKqZ2/9F/+UTP8rl/oYUg==', #89
                'U2FsdGVkX1/HYmkLrhoUJsxaxEwPbMqFYHyPfO9uk/r/xyQj6sJ9c8g6OGC+JMIvLYNCHvUhJ5cA1tci6X5r92vGvN2hkb6Iuh9ZndNyIWfL3GUc3RSrURhtMwhmPFHVn3QY7odroHREkRJE4zWd2q2rWNB+ss75RgBbkNNaGzCmvf3dXNoNSw7YKAwte2uOXbWqCIIygawRWB4a5ttXRmA/JWgTOUJhQH8OSk1Z0nzMlZiH/wrTY/0mTti+A9II47GDqdDtgKa7rc4tbvSc/4pr388a9DkPBBqLmqUbB4U=', #69
                'U2FsdGVkX19aAM+Br0rvXDnn8sptxNd+hpnHjAs/KJhEgFHnk+GF9MRZ95mhBouM2TKv9JAYXn1J9nZgbgIVk2Y0dX4dTurKDnIL/DpKUlyXtVefWrOLbQco1WzrYSAxbNTYmkuVPn5sGYmPoDtO5gYKyzD13vV8FMHJizic2IdH0LPgtJgvR4xmT/dFp0wQUYufaNPRG/CvbiUSP/J7pjBRy5B+3B0KlmuE/EzaXva15zHIlE7/X3wIQG3EyLkudJI9vzdZzhqeiZmEf1vH4g==', #68
                'U2FsdGVkX1+/JsyRuE9q/CXZsL6JsQ+ti2Kp91EmylsnqccxMHiveY50gRSDxiafg2+5rlB/9lp1Hyw2fOYBoLnRBO1FQBcDA6R/pjesSRhkECvwx6bAD+OHA0oAMgtifFAlsimyhkWNu2jLOrWNLs2cFWGoQ8QNNAqm8p8hMNZBv60/+epB5R8kfcA3eIUHroZhGhiZi6Hzrioqm7wsikBf2F831NQLbAwOKM4ZO/CrRWGtq/Ii6OcwYFexjgFZZJm3RsykUU8GnmR63GisHQ==', #67
                'U2FsdGVkX18a0h3dz63XBvyEKtg9SAsmKONefxrSdoTQKmM7+Apsktq8tMsI20sek5/0Dggnm5LCWc/X5vlKx+VLbjhQS9CJ7VGXJA+DBkt8FaTNK+IjuA6c+vyIK8/GFmQVmPkTsnVS9v+erKyWFDndPs3LYwl09bDwRH15UAW32brSIwsitbtxyl2QdoHQm1DjqZawwnV6PrYEC1zEqNRUeX6fBKMlD9N+JrK3FEt9NDm5tUldQLmnXqZVXHcVP5fecbChWML3l7DcRBbmCg==', #66
                'U2FsdGVkX18MX7/EN9CraF2/8AcF+o6ccSrAjLeBfncFj+FzP2kt6CbuP4JjgLsItS5Kf2rv6Fa0C9SFN91jA7xWuBbkV/QhC1ZukK0Y5bt3FFvR75QE92Wd/JKseCDzrCkEqGypuss7cG0svZyS2gO9iKAMWUIHybEl9sMwyp3ZNNyF1hg3KCMO5gcmAf+aO7KVCj7QAW0QB9L6bqP12r33oYa4K+RkG+YjRkw6qC8ddzK+yac52NzicwlMNwPOA9xW+7XpfuigXUUJ1U8Vng==', #65
                'U2FsdGVkX1/hSG9gDCYT5unlm9JCRGeIbNtoO5sv+AakYWZ//6QUAmv3Yp9AKA0KsKS4LURQtsUdgeuL2a2xZqX87aJcEWB54qfVCXX6ys8ZnhcPev1R3EYvVviewmRJH8i4V0YZ/TsVzQY89Y9+He8ePBleQkQKfXmx3tEtlHMiHTlN/IQPzfbJcbL2hsygegJOm0Aw/nWDy5DwIbsj8oh3Y9Ang0geA73pPgO5OCLqxexwq2A+R0U/q+01AXE0gNWhL7aswo3h827SZz1+kQ==', #64
                'U2FsdGVkX18fbKstE9wcCCXyqTKOmPwrRr+VEIrEgvAmcxVjC/H/QVWRcvOhiCwUWUGy0LcQSxOB5fQNj47+7mF41K0Yn25piKE7mI9PHMsjNvlKYbFYsC9btcKIl0UdQJ7pR6BRsTOfo9fIjgQkIRyKtkDJFIMvU1S5OaC51URo1x942Tps4i1VOEaUKuAZ18fsQtVwpbolO3kaiL7zePsl38mcNO+v0/bXl3v1zPMxBu3Je9s0w6x93aW2p+Yboc/HzT803jsDEUOQqOQNNA==', #63
                'U2FsdGVkX18gangVxqWtNquxn4H7S2xzf6b58uUHn6b757aaEPlIBYOEqJz7YwarCOQx42SgYGoyxRVM/PX4r2knERwf7UJpvrpIsuNcoq2F0wG2OElsiazdwDXJT8RZhDezBEdSiIVM4ZfPYqfzUyi05KSnFKVghYQaics4t4oM6VVYwnqSFXxlEvp+QDifSEKdsSJfgtnmmiScaRF1GXVO3cow8GZMAqSQYKXyW9ToMnm+Ifs6mysIu6xsA1fcFmPuc1sheFlmmdb66oq1cA==', #62
                'U2FsdGVkX192yU3SlRxgLd7KDBhcU9DNTj/qRBm0G+HlMhnUWbMYp5ZvSDcWvrM3EjpImiW3nXBq1n3+WTrKA42oYxwdvG5C3v6fyiAL9tlSOFDaTnHH7e4Ya5Hf9TjXk81xJOuu69RJxpxzCnZcU43WXPN+RTIb5YPVO83qE7p/vq/hAmCxgePYOTli1mHIHJ1h9yFXA5mXPzonjDvXNFDlY4uCJIiRxPEWCB/ya9icixkIT481N91BsiMEiTFDARmsyQSb3DTJaCR6WIJf5Q==', #61
                'U2FsdGVkX1+zNp++kdQxXEe6nIau3vHugYg0pRdFxk2AvrxxY/7z+Twp4NNv2nDCFL7ieA1Ii4rBVuwht1UCxLpRMgI4H+tIttN9mQ3CZtwDBshNhNt52MsIyuIL9Ha/ZO6QvH93zZhRgbhIizu5bRV3zIW2nmn9DhCy7+7JpPww3MKg6roPU4YyoxkGEtg5feSzYHXt8++s/KJHfA2qQgGFqWKHCCMpyyYb9HFQpFmPdFDmYP69Fr8+Iu9v3/MbTl/7+SH83ag4+A91r3Qiyw==', #60
                ] 

    start_time = time.time()

    index_name_today = get_index_name('se_engine')
    index_name_yesterday = get_index_name('se_engine', offset_days=1)

    es = Elasticsearch(
        cloud_id='elastic-id',
        basic_auth=('user', 'password'),
        request_timeout=30
    )



    def post_to_elasticsearch(results):
        if not results:  
            print("No results to post to Elasticsearch.")
            return
        index_name_today = get_index_name('se_engine')
        if not es.indices.exists(index=index_name_today):
            with open("se_engine_map.json", "r") as f:
                mapping = json.load(f)
            es.indices.create(index=index_name_today, body={"mappings": mapping})
            print(f"Index {index_name_today} created with predefined mapping.")

        unique_results = {}
        for result in results:
            domain = result.get('domain')
            if domain:
                # This will ensure that for each domain, only the last document is kept
                unique_results[domain] = result

        actions = []
        all_domains = list(unique_results.keys())

        # Batch check for document existence in both today's and yesterday's index
        existence_map_today = batch_check_documents_exist(es, [index_name_today], all_domains)
        existence_map_yesterday = batch_check_documents_exist(es, [index_name_yesterday], all_domains)

        for domain, result in unique_results.items():
            cleaned_result = remove_empty_or_none(result)
            flattened_result = flatten_list_fields(cleaned_result)
            
            # Check the existence maps to decide where to insert/update the document
            if existence_map_today.get(domain):
                actions.append({
                    "_op_type": "update",
                    "_index": index_name_today,
                    "_id": domain,
                    "doc": flattened_result
                })
            elif existence_map_yesterday.get(domain):
                actions.append({
                    "_op_type": "update",
                    "_index": index_name_yesterday,
                    "_id": domain,
                    "doc": flattened_result
                })
            else:
                flattened_result['pulled'] = 'no' # Only set 'pulled' field for new documents
                actions.append({
                    "_op_type": "index",
                    "_index": index_name_today,
                    "_id": domain,
                    "_source": flattened_result
                })

        response, failed = helpers.bulk(es, actions)
        print(response)
        success = len(actions) - len(failed)
        print(f"Successfully indexed {success} documents. Failed to index {len(failed)} documents.")

    def fetch_and_post(hashes):
        fetched_results = iris_investigate_api(hashes)
        post_to_elasticsearch(fetched_results)

    for search_hash in initial_hashes:
        fetch_and_post([search_hash])

    end_time = time.time()
    print(f"Script execution time: {end_time - start_time:.2f} seconds")

if __name__ == '__main__':
    main(None, None)


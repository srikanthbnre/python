#!/usr/bin/env python

import getopt
import logging
import sys
import requests
import traceback

##################################################
# Global Variables
##################################################
debug_mode = False
url = 'https://app.harness.io/gateway/api/graphql?accountId=6dEUvjDSSMO1UDSwR60D_w'
apiKey = "NmRFVXZqRFNTTU8xVURTd1I2MERfdzo6eUtMREJBN2NTVHA1TlJ4dDFpQ2Y0S3FuN08ySHpEVThjUWlLcHN5dnpqZVk3YTYzZnl3d2JZY0JSUG5MWkZnYnBCZkZNdzlBRXhxZml0NWM="
cli_input = {
    "sm_name": "",  # secret manager name
    "secrets_names": [],
    "secrets_values": [],
}

usage_definition = f'''
    Create single or multiple encrypted secrets using the SecretManager name.
    
    Usage: 
    
    python addsecret.py --secretmanagername 'SecretManager name' --secret_names "first, second, third" --secret_values "value1, value2, value3"
    or using the shortcuts for the arguments' names
    python addsecret.py -m 'SecretManager name ' -n "first, second, third" -v "value1, value2, value3"
    
    Example:
        python addsecret.py -m "Harness Secrets Manager - GCP KMS" -n "Amazon password, Google cloud password, Azure credentials" -v "AmaZonPwd, GCpWd, aZurEpWd"
            In this case the created secrets will obtain the values:
                "Amazon password": "AmaZonPwd"
                "Google cloud password": "GCpWd"
                "Azure credentials": ""aZurEpWd"
    
    -m or --secretmanagername: SecreteManager entity name as it is shown in 
        Harness / Security / Secrets Management / Secret Managers section
    -n or --secret_names: Names of the secrets to be created. Comma separated list in double quotes. 
        Can contain single value.
    -v or --secret_values: Values of the secrets provided with -n or --secret_names option. 
        Comma separated list in double quotes. Should be ordered according to the secret names 
        so that each  secret_name has corresponding value in the values list. List can contain single value. 

    python ./createUser_Group.py -h
    or 
    python ./createUser_Group.py --help
    
        Print this help and exit

'''


########################################################
#   Parse Input Arguments
########################################################
def parse_input(argv):
    opts, args = getopt.getopt(argv, 'm: n: v: h',
                               ['help',
                                'secretmanagername=',
                                'secret_names=',
                                'secret_values=', ])

    if debug_mode:
        print(opts)

    if not (('--help', '') in opts or ('-h', '') in opts) and len(opts) < 3:
        logging.error(usage_definition)
        sys.exit(2)

    # Iterate the options and get the corresponding values
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print(usage_definition)
            sys.exit(0)
        if opt in ('-m', '--secretmanagername'):
            cli_input["sm_name"] = arg
        elif opt in ('-n', '--secret_names'):
            try:
                cli_input["secrets_names"] = [x.strip() for x in arg.split(',')]
            except Exception as err:
                logging.error(traceback.format_exc())
        elif opt in ('-v', '--secret_values'):
            try:
                cli_input["secrets_values"] = [x.strip() for x in arg.split(',')]
            except Exception as err:
                logging.error(traceback.format_exc())

    if debug_mode:
        print(f'''
        Arguments passed

        SecretManager name:  {cli_input["sm_name"]}
        Secret(s)' name(s): {cli_input["secrets_names"]}
        Secret(s)' value(s): {cli_input["secrets_values"]}
    ''')

    # if any of the command line arguments is Null or empty
    for key, val in cli_input.items():
        if not val:
            logging.error(usage_definition)
            raise ValueError(f'Value {key} is absent')
            sys.exit(2)

    # if secret's values and secret's names does not match
    if len(cli_input["secrets_names"]) != len(cli_input["secrets_values"]):
        logging.error(usage_definition)
        raise ValueError(f'Length of secret_names {len(cli_input["secrets_names"])} does not match length of '
                         f'secret_values {len(cli_input["secrets_values"])}')
        sys.exit(2)


########################################################
#   Make HTTP POST Request
########################################################
def http_request(query, variables, url):
    """
    Performs POST request to the web server
    :param query: Query to be sent to the server, string
    :param variables: Values to be substituted in the query
    :param url: URL to which the request will be sent
    :return: Response object as a dictionary
    """

    try:
        response = requests.post(url,
                                 json={'query': query, 'variables': variables},
                                 verify=False,
                                 headers={"X-Api-Key": apiKey})
        response.raise_for_status()
        # Additional code will only run if the request is successful
        response_json = response.json()
        if "errors" in response_json:
            print("Request processing failed due to an error....")
            if debug_mode:
                print(response_json)
            return response_json
        else:
            print("Request has been successfully completed....")
            if debug_mode:
                print(response_json)
            return response_json
    except requests.exceptions.HTTPError as errh:
        print(errh)
    except requests.exceptions.ConnectionError as errc:
        print(errc)
    except requests.exceptions.Timeout as errt:
        print(errt)
    except requests.exceptions.RequestException as err:
        print(err)


########################################################
#   Get SecretManagerID using SecretManagerName
########################################################
def get_sm_id_by_name(sm_name):
    """
    Returns the ID of the SecretManager found by its canonical name
    :param sm_name:  Name of the secret manager, e.g. "Harness Secrets Manager - GCP KMS", string
    :return: ID of the SecretManager entity in the Harness system, string
    """

    query = """query{
  secretManagerByName(name: \"""" + sm_name + """"){
    id
    name
    usageScope {
      appEnvScopes {
        application {
          filterType
          appId
        }
        environment {
          filterType
          envId
        }
      }
    }
  }
}"""
    query_variables = {"name": sm_name}
    response_json = http_request(query, query_variables, url)
    sm_id = None
    if ' Secret Manager does not exist' not in str(response_json):
        sm_id = response_json['data']['secretManagerByName']['id']
    return sm_id


########################################################
#   Create User and assign it to the group(s)
########################################################
def create_secrets(sm_id, names, values):
    """
    Creates new encrypted secrets in the Harness system
    :param sm_id: ID of the SecretManager to be used for the secrets creation , e.g "8RQh_LdoP0CsTshrwahyIt", string
    :param names: list of the names for the new secrets, list of strings
    :param values: list of the values for the secrets, named in the "names" variable, list of strings
    :return: list of IDs for the newly created secrets, list of strings
    """

    query = """mutation($secret: CreateSecretInput!){
  createSecret(input: $secret){
    secret{
      id,
      name
      ... on EncryptedText{
        name
        secretManagerId
        id
      }
      usageScope{
        appEnvScopes{
          application{
            filterType
            appId
          }
          environment{
            filterType
            envId
          }
        }
      }
    }
  }
}
    """

    secrets_ids = []
    for n, a_secret in enumerate(names):
        query_variables = {
            "secret": {
                "secretType": "ENCRYPTED_TEXT",
                "encryptedText": {
                    "name": a_secret,
                    "value": values[n],
                    "secretManagerId": sm_id,
                    "usageScope": {
                        "appEnvScopes": [
                            {"application": {"filterType": "ALL"},
                             "environment": {"filterType": "PRODUCTION_ENVIRONMENTS"}},
                            {"application": {"filterType": "ALL"},
                             "environment": {"filterType": "NON_PRODUCTION_ENVIRONMENTS"}}
                        ]
                    }
                }
            }
        }

        if debug_mode:
            print(query_variables)
            print('executing createUser API call')
        response_json = http_request(query, query_variables, url)
        secrets_ids.append(response_json["data"]["createSecret"]["secret"]["id"])
    return secrets_ids


########################################################
#   Main Method
########################################################
def main():
    parse_input(sys.argv[1:])
    sm_id = get_sm_id_by_name(cli_input["sm_name"])
    ids_list = create_secrets(sm_id, cli_input["secrets_names"], cli_input["secrets_values"])
    print(" Created secrets:")
    for an_id in ids_list:
        print('    '+str(an_id))


########################################################
#   Start
########################################################
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()

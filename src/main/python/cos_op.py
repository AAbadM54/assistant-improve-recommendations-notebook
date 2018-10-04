import datetime
from requests.utils import quote
import hashlib
import hmac
import pandas as pd
from contextlib import closing
from io import BytesIO


def get_hash(key, msg):
    """Generates keyed-hash for a message using HMAC
        Parameters
        ----------
        key: The starting key for the hash.
        msg: message value that will be hashed
     """
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def create_signature_key(key, datestamp, region, service):
    """Create a signing key based on AWS signature version 4
        Parameters
        ----------
        key: Secret access key
        datestamp: date and timestamp
        region: service region
        service: service name
    """
    key_date = get_hash(('AWS4' + key).encode('utf-8'), datestamp)
    key_region = get_hash(key_date, region)
    key_service = get_hash(key_region, service)
    key_signing = get_hash(key_service, 'aws4_request')
    return key_signing


def generate_link(filename, credentials, expiration):
    """Generate a signing downloadable link of a file
        Parameters
        ----------
        filename: file name
        credentials: Cloud Object Storage accessing credentials
        expiration: expiration time in seconds
    """
    region = ''
    http_method = 'GET'
    endpoint = 'https://' + credentials['host']

    cur_time = datetime.datetime.utcnow()
    timestamp = cur_time.strftime('%Y%m%dT%H%M%SZ')
    datestamp = cur_time.strftime('%Y%m%d')

    standardized_querystring = ('X-Amz-Algorithm=AWS4-HMAC-SHA256' +
                                '&X-Amz-Credential=' + credentials['access_key_id'] + '/' + datestamp + '/' + region +
                                '/s3/aws4_request' +
                                '&X-Amz-Date=' + timestamp +
                                '&X-Amz-Expires=' + str(expiration) +
                                '&X-Amz-SignedHeaders=host')

    standardized_querystring_url_encoded = quote(standardized_querystring, safe='&=')

    standardized_resource = '/' + credentials['BUCKET'] + '/' + filename

    payload_hash = 'UNSIGNED-PAYLOAD'
    standardized_headers = 'host:' + credentials['host']
    signed_headers = 'host'

    standardized_request = (http_method + '\n' +
                            standardized_resource + '\n' +
                            standardized_querystring_url_encoded + '\n' +
                            standardized_headers + '\n' +
                            '\n' +
                            signed_headers + '\n' +
                            payload_hash)

    # assemble string-to-sign
    hashing_algorithm = 'AWS4-HMAC-SHA256'
    credential_scope = datestamp + '/' + region + '/' + 's3' + '/' + 'aws4_request'
    sts = (hashing_algorithm + '\n' +
           timestamp + '\n' +
           credential_scope + '\n' +
           hashlib.sha256(standardized_request.encode('utf-8')).hexdigest())

    # generate the signature
    signature_key = create_signature_key(credentials['secret_access_key'], datestamp, region, 's3')
    signature = hmac.new(signature_key,
                         sts.encode('utf-8'),
                         hashlib.sha256).hexdigest()

    # create and send the request
    request_url = (endpoint + '/' +
                   credentials['BUCKET'] + '/' +
                   filename + '?' +
                   standardized_querystring_url_encoded +
                   '&X-Amz-Signature=' +
                   signature)
    return request_url


def generate_excel(dataframe_list, sheet_name_list, bucket=None, filename=None, upload=False, cos_client=None):
    """Generate a formatted excel file given a list of dataframes for measure notebook
        Parameters
        ----------
        dataframe_list: a list of dataframes
        sheet_name_list: a list of sheet names
        bucket: bucket name
        filename: output file name
        upload: indicate whether to update to Cloud Object Storage
        cos_client: a Cloud Object Storage client
    """
    with closing(BytesIO()) as output:
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        workbook = writer.book
        data_format1 = workbook.add_format({'bg_color': '#BBCCE2'})
        data_format2 = workbook.add_format({'bg_color': '#DEE6EF'})

        format_header = workbook.add_format({'text_wrap': True})

        workbook.formats[0].set_font_size(15)
        for df, name in zip(dataframe_list, sheet_name_list):
            df.to_excel(writer, sheet_name=name)
            worksheet = writer.sheets[name]
            worksheet.set_row(0, 30, format_header)
            for row in range(1, len(df) + 1, 2):
                worksheet.set_row(row, cell_format=data_format1)
                worksheet.set_row(row + 1, cell_format=data_format2)
                worksheet.set_column('A:A', 5)
                worksheet.set_column('B:B', 30)
                worksheet.set_column('C:C', 30)
                worksheet.set_column('D:D', 15)
                worksheet.set_column('F:G', 35)
                worksheet.set_column('H:AH', 20)
        writer.save()
        if upload:
            cos_client.put_object(Bucket=bucket, Key=filename, Body=output.getvalue())


def generate_excel_effectiveness(dataframe_list, sheet_name_list, bucket=None, filename=None, upload=False,
                                 cos_client=None):
    """Generate a formatted excel file given a list of dataframes for effectiveness notebook
        Parameters
        ----------
        dataframe_list: a list of dataframes
        sheet_name_list: a list of sheet names
        bucket: bucket name
        filename: output file name
        upload: indicate whether to update to Cloud Object Storage
        cos_client: a Cloud Object Storage client
    """
    with closing(BytesIO()) as output:
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        workbook = writer.book
        data_format1 = workbook.add_format({'bg_color': '#BBCCE2'})
        data_format2 = workbook.add_format({'bg_color': '#DEE6EF'})

        format_header = workbook.add_format({'text_wrap': True})

        workbook.formats[0].set_font_size(15)
        for df, name in zip(dataframe_list, sheet_name_list):
            df.to_excel(writer, sheet_name=name)
            worksheet = writer.sheets[name]
            worksheet.set_row(0, 20, format_header)
            for row in range(1, len(df) + 1, 2):
                worksheet.set_row(row, cell_format=data_format1)
                worksheet.set_row(row + 1, cell_format=data_format2)
                worksheet.set_column('A:A', 5)
                worksheet.set_column('B:D', 30)
        writer.save()
        if upload:
            cos_client.put_object(Bucket=bucket, Key=filename, Body=output.getvalue())
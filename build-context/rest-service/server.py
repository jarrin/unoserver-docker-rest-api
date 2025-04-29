import os, sys, base64, tempfile, io, time, shutil, datetime, traceback

from flask import Flask, request, jsonify, send_file
from werkzeug.exceptions import HTTPException, Unauthorized
from unoserver.client import UnoClient
from flask_caching import Cache

from src.helpers import log, handle_file
from src.helpers_convert import validate_convert_request_data

API_KEY = os.getenv('REST_API_KEY')

app = Flask(__name__)

cache_folder = f"{os.environ.get('HOME', "/home/worker")}/.cache/flask"
app.config['CACHE_TYPE'] = 'FileSystemCache'
app.config['CACHE_DIR'] =  cache_folder
app.config['CACHE_DEFAULT_TIMEOUT'] = os.environ.get('CONVERTION_CACHE', 3600)
cache = Cache(app)

@app.route('/convert', methods=['POST'])
def convert_file():
    # Check for auth key in headers
    auth = request.headers.get('x-api-key')
    if API_KEY != None and auth != API_KEY:
        raise Unauthorized("Invalid Authorization key. Be sure you have one set in the x-api-key header")

    payload = validate_convert_request_data(request.get_json())


    cache_result = handle_file(payload["data"], payload["bust"], cache)
  
    if cache_result["converted_base64"] is not None:
        cache_result["from_cache"] = True
        return send_response(payload, cache_result)
 
    print("Input size size ")
    print( sys.getsizeof(cache_result["input_bytes"]))

    with tempfile.TemporaryDirectory(dir=cache_folder) as tmpdir:
        log(f"created temporary directory {tmpdir}")
        tmpfile = os.path.join(tmpdir, 'result')
        print(tmpfile)
        client = UnoClient()
        res = client.convert(
            indata=cache_result["input_bytes"],
            outpath=tmpfile,
            convert_to=payload["convert_to"],
        )

        with open(tmpfile, 'rb') as f:
            output_bytes = f.read()

    output_base64 = base64.b64encode(output_bytes).decode('utf-8')


    result = {
        "converted_to": payload["convert_to"],
        "converted_base64": output_base64,
        "expires_at": datetime.datetime.fromtimestamp(time.time() + app.config['CACHE_DEFAULT_TIMEOUT']).strftime("%Y-%m-%d %H:%M:%S")
    }
    print(result["expires_at"])
    
    cache.set(cache_result["key"], result)

    result["output_bytes"] = output_bytes
    result["from_cache"] = False
    result["key"] = cache_result["key"]
    return send_response(payload, result)

def send_response(payload: dict, result: dict):

    if payload["write_to"] != "base64":
        result["output_bytes"] = base64.b64decode(result["converted_base64"])

    if payload["write_to"] in ["stream", "base64"]:
        # Send as stream
        if payload["write_to"] == "stream":
            mime_map = {
                "pdf": "application/pdf",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }
            return send_file(
                io.BytesIO(result["output_bytes"]),
                mimetype=mime_map.get(payload["convert_to"], "application/octet-stream"),
                as_attachment=True,
                download_name=payload["output_name"] if "output_name" in payload else f"converted.{payload["convert_to"]}"
            )
        # Send as base64 string
        else: 
            return send_convert_success(result, { "data_base64": result["converted_base64"]})
        
    # Don't send, write to specified path
    overwritten = write_file(payload, result)
    
    return send_convert_success(result, {"file" : payload["write_to"].removeprefix("/data"), "overwritten": overwritten})


def write_file(payload: dict, result: dict):
    will_overwrite = os.path.exists(payload["write_to"])
    backup_path = None
    try:
        if will_overwrite:
            backup_file = tempfile.NamedTemporaryFile(delete=False)
            backup_path = backup_file.name
            backup_file.close()
            
            shutil.copy2(payload["write_to"], backup_path)
            log(f"Created backup {backup_path}")

        with open(payload["write_to"], "wb") as f:
            f.write(result["output_bytes"])

    except Exception as e:
        log(f"Error occurred: {e}")
        
        if backup_path is not None and os.path.exists(backup_path):
            shutil.copy2(backup_path, payload["write_to"])
            log(f"Restored original file from {backup_path}")

        raise 

    finally:
        if backup_path is not None and os.path.exists(backup_path):
            os.remove(backup_path)
            log(f"Deleted backup {backup_path}")
        return will_overwrite

def send_convert_success(result: dict, data: dict):
    resp = {
        "message": "Succesfully converted!", 
        "from_cache": result["from_cache"], 
        "expires_at": result["expires_at"],
        "converted_to": result["converted_to"]
    } | data
    return send_success(resp)

def send_success(resp: dict):
    resp["success"] = True
    return jsonify(resp), 200

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({
            "success": False,
            "code": e.code,
            "name": e.name,
            "message": e.description,
        }), e.code
    else:
        # Other type of exception, dont write details to the response
        log(''.join(traceback.format_exception(type(e), e, e.__traceback__)), True)

        return jsonify({
            "success": False,
            "code": 500,
            "name": "Internal Server Error",
            "message": "Consult error logs"
        }), 500

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=8000)
    pass

# Example reading last sensor value
dataFile = None
try:  # urlopen not usable with "with"
    url = "http://" + host + "/api/get/%21s_HUM1"
    dataFile = urllib.urlopen(url, None, 20)
    data = dataFile.read(80000)
    print("HUM1=" + data.strip(delimiters))
except:
    print(u"URL=" + (url if url else "") + \
          u", Message=" + traceback.format_exc())
if dataFile:
    dataFile.close()

# Example reading all values of the last hour (60 minutes of 60 seconds)
dataFile = None
try:  # urlopen not usable with "with"
    url = "http://" + host + "/api/grafana/query"
    now = get_timestamp()
    gr = {'range': {'from': formatDateGMT(now - (1 * 60 * 60)), 'to': formatDateGMT(now)}, \
          'targets': [{'target': 'HUM1'}, {'target': 'HUM2'}, {'target': 'HUM3'}]}
    data = json.dumps(gr)
    print(data)
    dataFile = urllib.urlopen(url, data, 20)
    result = json.load(dataFile)
    if result:
        print(result)
        for target in result:
            # print target
            index = target.get('target')
            for datapoint in target.get('datapoints'):
                value = datapoint[0]
                stamp = datapoint[1] / 1000
                print(index + ": " + formatDate(stamp) + " = " + str(value))
except:
    print(u"URL=" + (url if url else "") + \
          u", Message=" + traceback.format_exc())
if dataFile:
    dataFile.close()

timestamp = get_timestamp()
# erase the current file and open the valve in 30 seconds
open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
# append to the file and close the valve 1 minute later
open("valve.txt", 'a').write(str(timestamp + 90) + ";0\n")
print("valve.txt ready.")
# sleep for 5 minutes (in seconds)
time.sleep(5 * 60)

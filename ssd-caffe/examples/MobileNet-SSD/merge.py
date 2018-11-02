import numpy as np  
import sys,os  
caffe_root = '/opt/movidius/ssd-caffe/'
sys.path.insert(0, caffe_root + 'python')  
import caffe  
 
train_proto = 'example/MobileNetSSD_train.prototxt'  #Don't change this
train_model = 'snapshot/mobilenet_iter_2204.caffemodel'  #Required: Edit this to your snapshot caffemodel
 
deploy_proto = 'example/MobileNetSSD_deploy.prototxt'  #Don't change this
save_model = 'deploy/MobileNetSSD_deploy_2035_person.caffemodel' #Optional BUT: Where you want to save the deploy model. MAKE SURE THE DIRECTORY EXISTS BEFOREHAND. CREATE IT MANUALLY
 
def merge_bn(net, nob):
    '''
    merge the batchnorm, scale layer weights to the conv layer, to  improve the performance
    var = var + scaleFacotr
    rstd = 1. / sqrt(var + eps)
    w = w * rstd * scale
    b = (b - mean) * rstd * scale + shift
    '''
    for key in net.params.keys():
        if type(net.params[key]) is caffe._caffe.BlobVec:
            if key.endswith("/bn") or key.endswith("/scale"):
                continue
            else:
                conv = net.params[key]
                # if not net.params.has_key(key + "/bn"):
                key_python3 = key + "/bn"
                if key_python3 in net.params:
                    for i, w in enumerate(conv):
                        key = key.replace('_new', '') # This is the line I added
                        nob.params[key][i].data[...] = w.data
                else:
                    print(key)
                    # bn = net.params[key + "/bn"]
                    # scale = net.params[key + "/scale"]
                    bn = net.params[[key]["bn"]]
                    scale = net.params[[key]["scale"]]
                    wt = conv[0].data
                    channels = wt.shape[0]
                    bias = np.zeros(wt.shape[0])
                    if len(conv) > 1: #[more_than_sign] 
                        bias = conv[1].data
                    mean = bn[0].data
                    var = bn[1].data
                    scalef = bn[2].data
 
                    scales = scale[0].data
                    shift = scale[1].data
 
                    if scalef != 0:
                        scalef = 1. / scalef
                    mean = mean * scalef
                    var = var * scalef
                    rstd = 1. / np.sqrt(var + 1e-5)
                    rstd1 = rstd.reshape((channels,1,1,1))
                    scales1 = scales.reshape((channels,1,1,1))
                    wt = wt * rstd1 * scales1
                    bias = (bias - mean) * rstd * scales + shift
                     
                    nob.params[key][0].data[...] = wt
                    nob.params[key][1].data[...] = bias
   
 
net = caffe.Net(train_proto, train_model, caffe.TRAIN)  
net_deploy = caffe.Net(deploy_proto, caffe.TEST)  
 
merge_bn(net, net_deploy)
net_deploy.save(save_model)
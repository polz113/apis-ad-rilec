<?php

namespace App\Http\Controllers;

use App\HRMasterUpdate;
use App\UserData;
use App\GroupAssignment;
use App\OUData;
use App\OURelation;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Datetime;

define("FIELDNAME_DELIMITER", ".");

define("IGNORED_FIELDS", ["veljaOd", "veljaDo", "datumSpremembe", "stevilkaSekvence"]);

class ApisHRMasterController extends Controller
{
    //
    private function set_dates($object, $dateobj, $generated_at){
        // Log::debug(print_r($dateobj, True));
        $object->valid_from = $dateobj['veljaOd'];
        $object->valid_to = $dateobj['veljaDo'];
        $object->changed_at = $dateobj['datumSpremembe'];
        $object->generated_at = $generated_at;
    }

    private static function sanitize_name($name){
        return preg_replace("/[^a-zA-Z0-9]+/", "", $name);
    }

    private function parseHRMasterUpdate($hrmaster_id, $hrdata){
	    /* Get timestamp */
        if (isset($hrdata['TimeStamp'])){
            $timestamp = new Datetime($hrdata['TimeStamp']);
        } else {
            $timestamp = now();
        }
        if (isset($hrdata['OE'])){
            foreach($hrdata['OE'] as $item){
                $uid = $item['OE_Id'];
                foreach($item['data'] as $d){
                    $ou = new OUData();
                    $ou->uid = $uid;
                    $ou->h_r_master_update_id = $hrmaster_id;
                    $this->set_dates($ou, $hrmaster_id, $d, $timestamp);
                    $ou->OU = $d['organizacijskaEnota'];
                    $ou->save();
                }
            }
        }
        if (isset($hrdata['NadrejenaOE'])){
            foreach($hrdata['NadrejenaOE'] as $item){
                $child_uid = $item['OE_Id']; 
                foreach($item['data'] as $d){
                    $ou_rel = new OURelation();
                    $ou_rel->h_r_master_update_id = $hrmaster_id;
                    $this->set_dates($ou_rel, $hrmaster_id, $d, $timestamp);
                    $ou_rel->child_uid = $child_uid;
                    $ou_rel->parent_uid = $d['id'];
                    $ou_rel->save();
                }
            }
        }
        /* Set user data */
	    $userdata_array = array();
        $log = array();
        $dataitem = 0;
        foreach ($hrdata as $objname => $objlist){
            if (is_array($objlist)) {
                foreach ($objlist as $hritem){
                    if (isset($hritem['UL_Id'])){
                        $uid = $hritem['UL_Id'];
                        $infotip = $hritem['infotip'];
                        if (isset($hritem['podtip'])) {
                            $podtip = $hritem['podtip'];
                        } else {
                            $podtip = '0';
                        }
                        if (!isset($hritem['data'])) continue;
                        // Log::debug(print_r([$objname, $hritem], True));
                        foreach($hritem['data'] as $d) {
                            foreach ($d as $fieldname => $value){
                                if (in_array($fieldname, IGNORED_FIELDS)) continue;
                                $property = join(FIELDNAME_DELIMITER,
                                    [   $this->sanitize_name($objname),
                                        $this->sanitize_name($infotip),
                                        $this->sanitize_name($podtip),
                                        $this->sanitize_name($fieldname)]);
                                $userdata = new UserData();
                                $userdata->uid = $uid;
                                $userdata->h_r_master_update_id = $hrmaster_id;
                                $this->set_dates($userdata, $d, $timestamp);
                                $userdata->property = $property;
                                $userdata->dataitem = $dataitem;
                                $userdata->value = $value;
                                // TODO disable once we get bulk inserts below to work
                                $userdata->save();
                                $userdata_array[] = $userdata->AttributesToArray();
                            }
                            $dataitem += 1;
                        }
                    }
                }
            }
        }
    /* bulk insert - disabled because of date formatting issues */
/*
	Log::debug(print_r($userdata_array, True));*/
	// UserData::insert($userdata_array);
 
        return $log;
    }

    public function update(Request $request)
    {
        $hrmaster = new HRMasterUpdate();
        $hrdata = $request->post();
        $hrmaster->data = json_encode($hrdata);
        $hrmaster->save();
        
        try {
            return $this->parseHRMasterUpdate($hrmaster->id, $hrdata);
        // Validate the value...
        } catch (Throwable $e) {
            return response(['Error' => $e], 406);
        }
    }

    public function list(Request $request)
    {
        $res = array();
        foreach (HRMasterUpdate::all() as $record){
            $res[] = json_decode($record->data);
        }
        return $res;
    }

    public function show(Request $request)
    {
        return (["Tole", "Je", "Rezultat"]);
    }

}

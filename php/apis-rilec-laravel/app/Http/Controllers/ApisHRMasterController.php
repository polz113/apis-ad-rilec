<?php

namespace App\Http\Controllers;

use App\HRMasterUpdate;
use App\UserData;
use App\GroupAssignment;
use App\OUData;
use App\OURelation;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Symfony\Component\HttpFoundation\StreamedResponse;
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
        if (isset($dateobj['datumSpremembe'])){
            $object->changed_at = $dateobj['datumSpremembe'];
        } else {
            $object->changed_at = $generated_at;
        }
        $object->generated_at = $generated_at;
    }

    private static function sanitize_name($name){
        return preg_replace("/[^a-zA-Z0-9_]+/", "", $name);
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
                    $this->set_dates($ou, $d, $timestamp);
                    $ou->OU = $d['organizacijskaEnota'];
                    $ou->short_OU = $d['organizacijskaEnota_kn'];
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
                    $this->set_dates($ou_rel, $d, $timestamp);
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
        $clanice = [];
        foreach ($hrdata as $objname => $objlist){
            if (is_array($objlist)) {
                foreach ($objlist as $hritem){
                    if (isset($hritem['UL_Id'])){
                        $uid = $hritem['UL_Id'];
                        if (!isset($clanice[$uid])) {
                            $clanice[$uid] = array();
                        }
                        $hritem_valid_from = $hritem['veljaOd'];
                        $hritem_valid_to = $hritem['veljaDo'];
                        $kadrovska_item = [
                            "kadrovskaSt" => $hritem['kadrovskaSt'],
                            "veljaOd" => $hritem['veljaOd'],
                            "veljaDo" => $hritem['veljaDo'],
                        ];
                        // Log::debug(print_r($clanice, True));
                        $infotip = $hritem['infotip'];
                        if (isset($hritem['podtip'])) {
                            $podtip = $hritem['podtip'];
                        } else {
                            $podtip = '0';
                        }
                        if (!isset($hritem['data'])) continue;
                        foreach(array_merge($hritem['data'], [$kadrovska_item]) as $d) {
                            $clanica_userdata = new UserData();
                            $clanica_userdata->uid = $uid;
                            $clanica_userdata->h_r_master_update_id = $hrmaster_id;
                            $this->set_dates($clanica_userdata, $d, $timestamp);
                            $clanica_userdata->dataitem = $dataitem;
                            $clanica_userdata->property = "KadrovskiPodatki.0.0.clanica_Id";
                            $clanica_userdata->value = $hritem['clanica_Id'];
                            $clanica_userdata->save();
                            $userdata_array[] = $clanica_userdata->AttributesToArray();
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
/*
        $fake_date = [
            "veljaOd" => "0000-01-01",
            "veljaDo" => "9999-12-31",
        ];
        foreach ($clanice as $uid => $data_table){
            $uniq_data = array_intersect_key($data_table, array_unique(array_map('serialize', $data_table)));
            foreach ($uniq_data as $d){
                foreach (["clanica_Id", "kadrovskaSt"] as $property) {
                    $userdata = new UserData();
                    $userdata->uid = $uid;
                    $userdata->h_r_master_update_id = $hrmaster_id;
                    $this->set_dates($userdata, $fake_date, $timestamp);
                    $userdata->property = "KadrovskiPodatki.0.0." .$property;
                    $userdata->dataitem = $dataitem;
                    $userdata->value = $d[$property];
                    // Log::debug(print_r($userdata, True));
                    $userdata->save();
                    $userdata_array[] = $userdata->AttributesToArray();
                }
                $dataitem += 1;
            }
        }*/
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

    public function index(Request $request)
    {
        $res = new StreamedResponse(function(){
            $handle = fopen('php://output', 'w');
            fwrite($handle, '[');
            $first = True;
            foreach (HRMasterUpdate::cursor() as $record){
                if (!$first) fwrite($handle, ',');
                fwrite($handle, $record->data);
                $first = False;
            }
            fwrite($handle, ']');
            fclose($handle);
        });
        /*, 200, [
                'Content-Type' => 'text/csv',
                'Content-Disposition' => 'attachment; filename="export.csv"',
        ]);*/
        return $res;
    }

    public function show(Request $request)
    {
        return (["Tole", "Je", "Rezultat"]);
    }

}

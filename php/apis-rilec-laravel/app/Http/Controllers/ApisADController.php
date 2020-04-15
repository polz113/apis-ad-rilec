<?php

namespace App\Http\Controllers;

use App\HRMasterUpdate;
use App\GroupAssignment;
use App\OUAssignment;
use Illuminate\Http\Request;

class ApisADController extends Controller
{
    //
    public function update(Request $request)
    {
        $hrmaster = new HRMasterUpdate();
        $data = json_encode($request->post());
        $hrmaster->data = $data;
        $hrmaster->save();
        return '';
    }
    public function list(Request $request){
        return HRMasterUpdate::all();
    }
    public function show(Request $request)
    {
        return (["Tole", "Je", "Rezultat"]);
    }

}

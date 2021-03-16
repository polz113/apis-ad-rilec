<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\UserData;
use Carbon\Carbon;
use App\Http\Controllers\ApisOUController;
use Illuminate\Support\Facades\Log;

class ApisUserDataController extends Controller
{
    //
    public function index(Request $request, $date = Null){
        if (is_null($date)) {
            $date = Carbon::now();
        }
        return UserData::properties_at_timestamp($date);
    }

    public function show(Request $request, $date, $id){
        $properties = UserData::whereDate('valid_from', '<=', $date)
            ->whereDate('valid_to', '>=', $date)
            ->where('uid', '=', $id)
            ->orderBy('property')
            ->orderBy('changed_at')
            ->orderBy('generated_at')
            ->get();
        $user = array();
        foreach ($properties as $entry){
            $prop = $entry['property'];
            if (in_array($prop, $user)){
                break;
            }
            $user[$prop] = $entry['value'];
        }
        return $user;
    }

}

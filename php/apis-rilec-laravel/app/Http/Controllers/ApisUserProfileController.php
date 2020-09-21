<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use ApisOUController;
use App\UserData;

class ApisUserProfileController extends Controller
{
    //
    public function index(Request $request, $date){
        $properties = UserData::whereDate('valid_from', '<=', $date)
            ->whereDate('valid_to', '>=', $date)
            ->orderBy('uid')
            ->orderBy('changed_at')
            ->orderBy('generated_at')
            ->orderBy('property')
            ->get();
        $users = array();
        $old_uid = Null;
        foreach ($properties as $entry){
            if ($entry['uid'] != $old_uid){
                if ($old_uid != Null){
                    $users[] = $user;
                }
                $user = array();
                $user['uid'] = $entry['uid'];
                $old_uid = $entry['uid'];
            }
            $prop = $entry['property'];
            if (!in_array($prop, $user)) {
                $user[$prop] = $entry['value'];
            }
        }
        $users[] = $user;
        return $users;
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

    public function tree_index(Request $request, $date){
        $tree = ApisOUController.tree_index($request, $date);

        return $tree;
    }
}

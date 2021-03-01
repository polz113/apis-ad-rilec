<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\ADDataset;
use Carbon\Carbon;

class ADDatasetController extends Controller
{


    public function show(Request $request, $id){
        return ADDataset::where('id', $id)->first();
    }

    public function index(Request $request){
        return ADDataset::get();
    }

    public function create(Request $request, $timestamp = Null){
        if (is_null($timestamp)) {
            $timestamp = Carbon::now();
        }
        $dataset = new ADDataset();
        $dataset->save();
        return([]);
    }
}

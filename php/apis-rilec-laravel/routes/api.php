<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
| Here is where you can register API routes for your application. These
| routes are loaded by the RouteServiceProvider within a group which
| is assigned the "api" middleware group. Enjoy building your API!
|
*/

Route::group(['middleware'=>'auth:api'], function(){
    /* Route::put('/replicate', 'ApisADController@update'); 
    Route::get('/replicate', 'ApisADController@list'); */
    Route::put('/hr/HRMaster/replicate', 'ApisHRMasterController@update');
    Route::get('/hr/HRMaster/replicate', 'ApisHRMasterController@list');
    Route::get('/api/userprofile/{date}', 'ApisUserProfileController@index');
    Route::get('/api/userprofile/{date}/{id}', 'ApisUserProfileController@show');
    Route::get('/api/user_tree/{date}/{id}', 'ApisUserProfileController@tree_index');
    Route::get('/api/ou/{date}', 'ApisOUController@index');
    Route::get('/api/ou_tree/{date}', 'ApisOUController@tree_index');
    Route::get('/api/ou/{date}/{id}', 'ApisOUController@show');
    /*
    Route::get('/user', function (Request $request) {
    return $request->user();
  }); */
});
